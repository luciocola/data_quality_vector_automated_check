"""
UMM STAC Converter - Main Plugin Class
"""
import os.path
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsMessageLog, Qgis

# Import resources but defer dialog import to avoid premature UI loading
from .resources import *


class UMMSTACConverter:
    """QGIS Plugin Implementation for UMM-STAC Conversion."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'UMMSTACConverter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr('&UMM STAC Converter')
        self.toolbar = self.iface.addToolBar('UMMSTACConverter')
        self.toolbar.setObjectName('UMMSTACConverter')
        
        self.dlg = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('UMMSTACConverter', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/umm_stac_converter/icon.png'
        self.add_action(
            icon_path,
            text=self.tr('UMM STAC DQ4EO Converter'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&UMM STAC Converter'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        
        try:
            # Import dialog here to avoid loading UI at plugin enable time
            from .converter_dialog import ConverterDialog
            
            # Create the dialog with elements (after translation) and keep reference
            # Only create GUI ONCE in callback, so that it will only load when the plugin is started
            if self.dlg is None:
                self.dlg = ConverterDialog()
                
            # Show the dialog
            self.dlg.show()
            result = self.dlg.exec_()
            
            if result:
                # User clicked OK - process the conversion
                self.log_message("Conversion completed", Qgis.Info)
        except Exception as e:
            self.log_message(f"Error initializing converter dialog: {str(e)}", Qgis.Critical)
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Plugin Error",
                f"Failed to initialize UMM STAC Converter:\n\n{str(e)}\n\nCheck the QGIS log for details."
            )
            import traceback
            traceback.print_exc()

    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log.
        
        :param message: Message to log
        :type message: str
        :param level: Message level (Info, Warning, Critical)
        :type level: Qgis.MessageLevel
        """
        QgsMessageLog.logMessage(message, 'UMM STAC Converter', level)
