import logging
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)

class ThemeManager:
    """Manages application themes and styling."""
    
    def __init__(self):
        self.theme = "light"  # Default theme
        self.color_theme = "blue"  # Default color theme
    
    def get_theme_colors(self, theme="light"):
        """
        Get the color palette for the specified theme.
        
        Args:
            theme (str): The theme name ('light', 'dark', 'blue', 'earth')
            
        Returns:
            dict: A dictionary of color values for different UI elements
        """
        # Define color schemes for different themes
        if theme == "dark":
            return {
                'figure_facecolor': '#222233',
                'axes_facecolor': '#2D2D44',
                'text_color': '#E1E1E1',
                'label_color': '#AAAAFF',
                'title_color': '#CCCCFF',
                'spine_color': '#444466',
                'grid_color': '#444466',
                'primary_color': '#4455BB',
                'secondary_color': '#5555AA',
                'accent_color': '#7777FF'
            }
        elif theme == "blue":
            return {
                'figure_facecolor': '#E8F0F8',
                'axes_facecolor': '#F8FAFF',
                'text_color': '#333355',
                'label_color': '#2244AA',
                'title_color': '#2244AA',
                'spine_color': '#AABBCC',
                'grid_color': '#CCDDEE',
                'primary_color': '#4477CC',
                'secondary_color': '#55AADD',
                'accent_color': '#3388DD'
            }
        elif theme == "earth":
            return {
                'figure_facecolor': '#F0F0E8',
                'axes_facecolor': '#F8F8F0',
                'text_color': '#334433',
                'label_color': '#225522',
                'title_color': '#225522',
                'spine_color': '#BBCCAA',
                'grid_color': '#DDEEBB',
                'primary_color': '#447744',
                'secondary_color': '#669955',
                'accent_color': '#88AA66'
            }
        else:  # Default light theme
            return {
                'figure_facecolor': '#FFFFFF',
                'axes_facecolor': '#F8F8F8',
                'text_color': '#333333',
                'label_color': '#555555',
                'title_color': '#444444',
                'spine_color': '#CCCCCC',
                'grid_color': '#DDDDDD',
                'primary_color': '#4477AA',
                'secondary_color': '#5588AA',
                'accent_color': '#6699BB'
            }
    
    def get_theme_stylesheet(self, theme, color_theme):
        """Get the stylesheet for the specified theme."""
        # Base styling for controls
        button_style = """
            QPushButton {
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(dark);
            }
        """
        
        if theme == "dark":
            return f"""
                QWidget {{ background-color: #222233; color: #E1E1E1; }}
                QDialog {{ background-color: #222233; color: #E1E1E1; }}
                QTableWidget {{ 
                    background-color: #2D2D44; 
                    color: #E1E1E1; 
                    gridline-color: #444466;
                    border-radius: 4px;
                    border: 1px solid #444466;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #3F3F66; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #3F3F66; 
                    color: #E1E1E1; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #444466; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #E1E1E1; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: #333355; 
                    color: #E1E1E1; 
                    border: 1px solid #444466;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #5555AA;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #7777FF;
                }}
                QPushButton#actionButton {{ 
                    background-color: #4455BB; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #445588; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #774455; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #E1E1E1; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #555577;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #5555AA;
                }}
                QStatusBar {{ 
                    background-color: #2F2F44; 
                    color: #AAAACC;
                    border-top: 1px solid #444466;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #AAAAFF;
                }}
                QFrame#headerLine {{
                    color: #444466;
                }}
                QSplitter::handle {{
                    background-color: #444466;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #2D2D44;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #444466;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #5555AA;
                }}
            """
        elif color_theme == "blue" and theme == "light":
            return f"""
                QWidget {{ background-color: #F0F4F8; color: #333344; }}
                QDialog {{ background-color: #F0F4F8; color: #333344; }}
                QTableWidget {{ 
                    background-color: white; 
                    color: #333344;
                    gridline-color: #DDDDEE;
                    border-radius: 4px;
                    border: 1px solid #CCDDEE;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #3070B0; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #CCDDEE; 
                    color: #333355; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #CCDDEE; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #333355; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: white; 
                    color: #333355; 
                    border: 1px solid #CCDDEE;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #AABBDD;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #5588CC;
                }}
                QPushButton#actionButton {{ 
                    background-color: #3070B0; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #5588AA; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #AA5566; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #333355; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #AABBDD;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #3070B0;
                }}
                QStatusBar {{ 
                    background-color: #E0E8F0; 
                    color: #5577AA;
                    border-top: 1px solid #CCDDEE;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #2255AA;
                }}
                QFrame#headerLine {{
                    color: #CCDDEE;
                }}
                QSplitter::handle {{
                    background-color: #CCDDEE;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #F0F4F8;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #CCDDEE;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #AABBDD;
                }}
            """
        else:
            # Default light theme
            return f"""
                QWidget {{ background-color: #FAFAFA; color: #333333; }}
                QDialog {{ background-color: #FAFAFA; color: #333333; }}
                QTableWidget {{ 
                    background-color: white; 
                    color: #333333;
                    gridline-color: #DDDDDD;
                    border-radius: 4px;
                    border: 1px solid #DDDDDD;
                }}
                QTableWidget::item:selected {{ 
                    background-color: #4477AA; 
                    color: white;
                }}
                QHeaderView::section {{ 
                    background-color: #EEEEEE; 
                    color: #333333; 
                    padding: 5px;
                    border: none;
                }}
                QGroupBox {{ 
                    border: 1px solid #DDDDDD; 
                    border-radius: 4px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #444444; 
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                }}
                QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{ 
                    background-color: white; 
                    color: #333333; 
                    border: 1px solid #DDDDDD;
                    border-radius: 4px;
                    padding: 2px 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
                    border: 1px solid #BBBBCC;
                }}
                QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                    border: 1px solid #6688AA;
                }}
                QPushButton#actionButton {{ 
                    background-color: #4477AA; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#secondaryButton {{ 
                    background-color: #5588AA; 
                    color: white; 
                    {button_style}
                }}
                QPushButton#closeButton {{ 
                    background-color: #AA5566; 
                    color: white; 
                    {button_style}
                }}
                QCheckBox {{ color: #333333; }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 3px;
                    border: 1px solid #BBBBCC;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #4477AA;
                }}
                QStatusBar {{ 
                    background-color: #EFEFEF; 
                    color: #666666;
                    border-top: 1px solid #DDDDDD;
                }}
                QLabel#headerTitle {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #4477AA;
                }}
                QFrame#headerLine {{
                    color: #DDDDDD;
                }}
                QSplitter::handle {{
                    background-color: #DDDDDD;
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:vertical {{
                    height: 2px;
                }}
                QScrollBar:vertical {{
                    background-color: #FAFAFA;
                    width: 12px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical {{
                    background-color: #DDDDDD;
                    border-radius: 4px;
                    min-height: 20px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background-color: #BBBBCC;
                }}
            """
    
    def get_plot_theme_colors(self, theme, color_theme):
        """Get the plot colors for the specified theme."""
        if theme == "dark":
            return {
                'figure_facecolor': '#222233',
                'axes_facecolor': '#2D2D44',
                'text_color': '#E1E1E1',
                'label_color': '#E1E1E1',
                'title_color': '#AAAAFF',
                'spine_color': '#444466',
                'grid_color': '#444466'
            }
        elif color_theme == "blue" and theme == "light":
            return {
                'figure_facecolor': '#F0F4F8',
                'axes_facecolor': '#FFFFFF',
                'text_color': '#333344',
                'label_color': '#3070B0',
                'title_color': '#3070B0',
                'spine_color': '#CCDDEE',
                'grid_color': '#CCDDEE'
            }
        elif color_theme == "earth":
            return {
                'figure_facecolor': '#F5F5F0',
                'axes_facecolor': '#FFFFFF',
                'text_color': '#333322',
                'label_color': '#8B7355',
                'title_color': '#8B7355',
                'spine_color': '#CCBB99',
                'grid_color': '#DDDDCC'
            }
        else:
            return {
                'figure_facecolor': '#FFFFFF',
                'axes_facecolor': '#FFFFFF',
                'text_color': 'black',
                'label_color': 'black',
                'title_color': 'black',
                'spine_color': 'black',
                'grid_color': '#CCCCCC'
            }
    
    def apply_theme_to_plot(self, figure, ax, theme, color_theme):
        """Apply theme colors to a matplotlib plot."""
        colors = self.get_plot_theme_colors(theme, color_theme)
        
        figure.patch.set_facecolor(colors['figure_facecolor'])
        ax.set_facecolor(colors['axes_facecolor'])
        ax.tick_params(colors=colors['text_color'])
        ax.xaxis.label.set_color(colors['label_color'])
        ax.yaxis.label.set_color(colors['label_color'])
        ax.title.set_color(colors['title_color'])
        
        for spine in ax.spines.values():
            spine.set_color(colors['spine_color'])
        
        ax.grid(True, linestyle='--', alpha=0.5, color=colors['grid_color'])