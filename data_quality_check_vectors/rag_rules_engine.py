"""Local guideline retrieval/execution helper with optional Ollama integration.

This module provides a lightweight RAG-like workflow:
1) Ingest user guidelines from a JSON file
2) Retrieve relevant guidelines using keyword overlap scoring
3) Execute known guideline operations in a deterministic way
"""

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from datetime import datetime


class RuleStore:
    """Loads user-defined guidelines and provides simple lexical retrieval."""

    def __init__(self, rules_path):
        self.rules_path = rules_path
        self.rules = []
        self._load_rules()

    @property
    def rules_dir(self):
        return os.path.dirname(self.rules_path)

    @property
    def profiles_dir(self):
        return os.path.join(self.rules_dir, "profiles")

    def _load_rules(self):
        if not os.path.exists(self.rules_path):
            self.rules = []
            return
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self.rules = data
        else:
            self.rules = []

    def save_default_if_missing(self):
        if os.path.exists(self.rules_path):
            return
        default_rules = [
            {
                "id": "copyright-required",
                "name": "Copyright must be filled",
                "description": "Ensure copyright is not empty for all selected layers.",
                "keywords": ["copyright", "mandatory", "empty", "all"],
                "action": "require_field_not_empty",
                "params": {
                    "field": "copyright"
                }
            },
            {
                "id": "copyright-autofill",
                "name": "Autofill copyright with year",
                "description": "Fill empty copyright values with current year text.",
                "keywords": ["copyright", "fill", "date", "year"],
                "action": "set_field_if_empty",
                "params": {
                    "field": "copyright",
                    "value_template": "Copyright {year}",
                    "create_if_missing": True,
                    "fallback_to_full_layer_when_extent_empty": True
                }
            },
            {
                "id": "roads-elevation-snap-candidates",
                "name": "Road near-node elevation check",
                "description": "Find close road endpoints where elevation is equal and snapping is recommended.",
                "keywords": ["road", "elevation", "topology", "snap", "connect"],
                "action": "check_road_endpoint_snap_candidates",
                "params": {
                    "tolerance_m": 0.01,
                    "elevation_field": "elevation"
                }
            }
        ]
        os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(default_rules, f, indent=2)
        self.rules = default_rules

    def ensure_default_profiles(self):
        os.makedirs(self.profiles_dir, exist_ok=True)
        defaults = {
            "roads.json": [
                {
                    "id": "roads-elevation-snap-candidates",
                    "name": "Road near-node elevation check",
                    "description": "Find close road endpoints where elevation is equal and snapping is recommended.",
                    "keywords": ["road", "elevation", "topology", "snap", "connect"],
                    "action": "check_road_endpoint_snap_candidates",
                    "params": {
                        "tolerance_m": 0.01,
                        "elevation_field": "elevation"
                    }
                }
            ],
            "cadastre.json": [
                {
                    "id": "cadastre-owner-required",
                    "name": "Owner must be filled",
                    "description": "Ensure owner field is not empty for cadastral layers.",
                    "keywords": ["cadastre", "owner", "mandatory", "quality"],
                    "action": "require_field_not_empty",
                    "params": {"field": "owner"}
                }
            ],
            "emergency_response.json": [
                {
                    "id": "copyright-autofill",
                    "name": "Autofill copyright with date",
                    "description": "Fill empty copyright values with current date text.",
                    "keywords": ["copyright", "emergency", "fill", "date"],
                    "action": "set_field_if_empty",
                    "params": {
                        "field": "copyright",
                        "value_template": "Copyright {date}",
                        "create_if_missing": True,
                        "fallback_to_full_layer_when_extent_empty": True
                    }
                }
            ],
        }
        for name, rules in defaults.items():
            path = os.path.join(self.profiles_dir, name)
            if os.path.exists(path):
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2)

    def available_profiles(self):
        self.ensure_default_profiles()
        names = ["default"]
        for name in sorted(os.listdir(self.profiles_dir)):
            if name.lower().endswith(".json"):
                names.append(os.path.splitext(name)[0])
        return names

    def _profile_path(self, profile_name):
        if profile_name in (None, "", "default"):
            return self.rules_path
        return os.path.join(self.profiles_dir, profile_name + ".json")

    def load_profile(self, profile_name):
        path = self._profile_path(profile_name)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def append_rule_to_profile(self, profile_name, rule):
        path = self._profile_path(profile_name)
        existing = self.load_profile(profile_name)
        existing.append(rule)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    def save_profile(self, profile_name, rules):
        path = self._profile_path(profile_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)

    def active_rules(self, profile_name):
        base = self.load_profile("default")
        if profile_name in (None, "", "default"):
            return base
        profile_rules = self.load_profile(profile_name)
        merged = list(base)
        seen = {r.get("id") for r in merged}
        for rule in profile_rules:
            rid = rule.get("id")
            if rid not in seen:
                merged.append(rule)
                seen.add(rid)
        return merged

    @staticmethod
    def _tokenize(text):
        return set(re.findall(r"[a-z0-9_]+", (text or "").lower()))

    def retrieve(self, query, top_k=5):
        return self.retrieve_with_rules(self.rules, query, top_k=top_k)

    def retrieve_with_rules(self, rules, query, top_k=5):
        query_tokens = self._tokenize(query)
        scored = []
        for rule in rules:
            text = " ".join([
                rule.get("name", ""),
                rule.get("description", ""),
                " ".join(rule.get("keywords", [])),
                rule.get("action", ""),
            ])
            rule_tokens = self._tokenize(text)
            overlap = len(query_tokens.intersection(rule_tokens))
            if overlap > 0:
                scored.append((overlap, rule))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [rule for _, rule in scored[:top_k]]


class OllamaClient:
    """Small client for local Ollama embedding and chat endpoints."""

    def __init__(self, base_url, model):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or "nomic-embed-text"

    def _post_json(self, endpoint, payload, timeout=25):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def embed(self, text):
        try:
            out = self._post_json(
                "/api/embeddings",
                {"model": self.model, "prompt": text},
            )
        except urllib.error.URLError:
            return None
        return out.get("embedding")

    def generate_rule_json(self, prompt):
        schema_prompt = (
            "You convert plain-language quality guideline requests into strict JSON. "
            "Return ONLY compact JSON with keys: id,name,description,keywords,action,params. "
            "Allowed operation values (in key action): require_field_not_empty, set_field_if_empty, check_road_endpoint_snap_candidates, create_bridge_segment_at_road_river_crossing. "
            "Operation guidance: "
            "require_field_not_empty => params {field}. "
            "set_field_if_empty => params {field,value_template,create_if_missing,fallback_to_full_layer_when_extent_empty}. "
            "check_road_endpoint_snap_candidates => params {tolerance_m,elevation_field,select_candidates}. "
            "create_bridge_segment_at_road_river_crossing => params {road_layer_contains,river_layer_contains,name_field,name_value,segment_half_length,create_if_missing}. "
            "Create a short kebab-case id. keywords must be a JSON array of short strings. "
            "If unsure, choose require_field_not_empty with best guess for params.field. "
            "User request: " + prompt
        )
        out = None
        for model_name in (self.model, "llama3.2"):
            try:
                out = self._post_json(
                    "/api/generate",
                    {
                        "model": model_name,
                        "prompt": schema_prompt,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                if out and out.get("response"):
                    break
            except urllib.error.URLError:
                continue
        if out is None:
            return None
        text = out.get("response", "").strip()
        if not text:
            return None
        return self._extract_first_json_object(text)

    def generate_params_json(self, action, plain_text):
        action = (action or "require_field_not_empty").strip()
        prompt = (
            "Convert the user text into a JSON object for guideline params. "
            "Return ONLY compact JSON object and nothing else. "
            "Operation is: " + action + ". "
            "Allowed keys by operation: "
            "require_field_not_empty: field. "
            "set_field_if_empty: field, value_template, create_if_missing, fallback_to_full_layer_when_extent_empty. "
            "check_road_endpoint_snap_candidates: tolerance_m, elevation_field, select_candidates. "
            "create_bridge_segment_at_road_river_crossing: road_layer_contains, river_layer_contains, name_field, name_value, segment_half_length, create_if_missing. "
            "User text: " + plain_text
        )
        out = None
        for model_name in (self.model, "llama3.2"):
            try:
                out = self._post_json(
                    "/api/generate",
                    {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                if out and out.get("response"):
                    break
            except urllib.error.URLError:
                continue
        if out is None:
            return None
        text = out.get("response", "").strip()
        if not text:
            return None
        parsed = self._extract_first_json_object(text)
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _extract_first_json_object(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not m:
                return None
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None


class EmbeddingRetriever:
    """Embeddings-based retrieval with lexical fallback."""

    @staticmethod
    def _rule_text(rule):
        return " ".join([
            rule.get("name", ""),
            rule.get("description", ""),
            " ".join(rule.get("keywords", [])),
            rule.get("action", ""),
            json.dumps(rule.get("params", {}), sort_keys=True),
        ])

    @staticmethod
    def _cosine(a, b):
        if not a or not b or len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return -1.0
        return dot / (na * nb)

    def retrieve(self, rules, query, client, top_k=5):
        qv = client.embed(query)
        if not qv:
            return []
        scored = []
        for rule in rules:
            rv = client.embed(self._rule_text(rule))
            if not rv:
                continue
            scored.append((self._cosine(qv, rv), rule))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [rule for score, rule in scored[:top_k] if score > 0]


def sanitize_rule(rule):
    """Normalize a generated guideline and enforce required keys."""
    if not isinstance(rule, dict):
        return None
    name = (rule.get("name") or "Generated Guideline").strip()
    action = (rule.get("action") or "require_field_not_empty").strip()
    params = rule.get("params") if isinstance(rule.get("params"), dict) else {}
    keywords = rule.get("keywords") if isinstance(rule.get("keywords"), list) else []
    rid = rule.get("id") or ("generated-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:10])
    return {
        "id": rid,
        "name": name,
        "description": rule.get("description") or "Generated from natural language prompt.",
        "keywords": [str(x).strip() for x in keywords if str(x).strip()],
        "action": action,
        "params": params,
    }


class RuleExecutor:
    """Executes known operations over provider features."""

    @staticmethod
    def render_template(value_template):
        now = datetime.now()
        return value_template.format(
            year=now.year,
            date=now.strftime("%Y-%m-%d")
        )
