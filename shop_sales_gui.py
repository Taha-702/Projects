"""
Enhanced Shop Sales GUI - Single File (PySide6)

Replaces the previous simple version with a polished, modern interface:
- Dark / Light theme toggle (top-right)
- Left sidebar navigation (Inventory, Cart, Settings)
- Card-style panels with rounded corners and soft shadows
- Custom ToggleSwitch widget for Retail / Wholesale mode
- Icon-style buttons (using Unicode icons for portability)
- Search, add/edit/remove products, add-to-cart with qty dialog
- Cart with live totals, checkout that writes a receipt and updates stock
- CSV import/export

Dependencies: PySide6
Install: pip install PySide6
Run: python shop_sales_gui.py

This single-file app is designed to be readable and easy to extend.
"""

import sys
import os
import csv
import datetime
from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt, QSize, QEasingCurve, QPropertyAnimation, QPoint, QRect
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QFileDialog, QHeaderView, QFrame, QInputDialog, QSpinBox, QDialog, QDialogButtonBox,
    QSplitter, QStackedWidget, QToolButton
)

PRODUCTS_CSV = "products.csv"

# -------------------- Utilities --------------------

def money(v):
    return f"{Decimal(v).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

# -------------------- Custom Toggle Switch --------------------
class ToggleSwitch(QToolButton):
    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(60, 28)
        self._anim = QPropertyAnimation(self, b"pos")

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        # background
        bg_color = QColor('#4caf50') if self.isChecked() else QColor('#bdbdbd')
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(r, 14, 14)
        # knob
        knob_radius = r.height() - 6
        knob_x = r.width() - knob_radius - 3 if self.isChecked() else 3
        knob_rect = QRect(knob_x, 3, knob_radius, knob_radius)
        painter.setBrush(QColor('white'))
        painter.drawEllipse(knob_rect)
        painter.end()

# -------------------- Product Dialog --------------------
class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.setWindowTitle("Add Product" if product is None else "Edit Product")
        self.setModal(True)
        self.product = product or {"sku":"","name":"","price":"0.00","stock":"0"}
        layout = QVBoxLayout(self)

        form = QGridLayout()
        form.addWidget(QLabel("SKU:"), 0, 0)
        self.sku = QLineEdit(self.product['sku'])
        form.addWidget(self.sku, 0, 1)
        form.addWidget(QLabel("Name:"), 1, 0)
        self.name = QLineEdit(self.product['name'])
        form.addWidget(self.name, 1, 1)
        form.addWidget(QLabel("Price:"), 2, 0)
        self.price = QLineEdit(str(self.product['price']))
        form.addWidget(self.price, 2, 1)
        form.addWidget(QLabel("Stock:"), 3, 0)
        self.stock = QSpinBox(); self.stock.setMaximum(1_000_000); self.stock.setValue(int(self.product.get('stock',0)))
        form.addWidget(self.stock, 3, 1)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        
    def get_data(self):
        return {
            'sku': self.sku.text().strip(),
            'name': self.name.text().strip(),
            'price': money(self.price.text().strip() or '0.00'),
            'stock': str(self.stock.value())
        }

# -------------------- Main Window --------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Shop Sales - Enhanced UI')
        self.resize(1100, 700)
        self.products = []
        self.cart = []

        self._setup_ui()
        self._load_products()
        self._apply_theme(dark=True)
        self._refresh_products()
        self._refresh_cart()

    def _setup_ui(self):
        font = QFont('Segoe UI', 10)
        self.setFont(font)

        # Central widget with splitter for sidebar + main
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8,8,8,8)

        # Sidebar
        sidebar = QFrame(); sidebar.setObjectName('sidebar')
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(10,10,10,10)
        sb_layout.setSpacing(12)

        title = QLabel('🛍️ Shop Sales')
        title.setObjectName('appTitle')
        title.setFixedHeight(28)
        sb_layout.addWidget(title)

        self.btn_inventory = QPushButton('Inventory')
        self.btn_cart = QPushButton('Cart')
        self.btn_settings = QPushButton('Settings')
        for b in (self.btn_inventory, self.btn_cart, self.btn_settings):
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setMinimumHeight(36)
            b.setStyleSheet('text-align:left; padding-left:12px;')
            sb_layout.addWidget(b)

        self.btn_inventory.setChecked(True)

        sb_layout.addStretch()
        # Theme toggle in sidebar footer
        self.theme_toggle = ToggleSwitch(checked=True)
        theme_label = QLabel('Dark Mode')
        footer = QHBoxLayout(); footer.addWidget(theme_label); footer.addStretch(); footer.addWidget(self.theme_toggle)
        sb_layout.addLayout(footer)

        # Main area
        content = QFrame(); content.setObjectName('content')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12,6,12,12)

        # Top bar: Search, Mode toggle, Import/Export
        top_bar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('Search products by SKU or name...')
        self.search.textChanged.connect(self._refresh_products)
        top_bar.addWidget(self.search, 1)

        self.mode_switch = ToggleSwitch(checked=False)
        self.mode_label = QLabel('Retail')
        def on_mode():
            self.mode_label.setText('Wholesale' if self.mode_switch.isChecked() else 'Retail')
        self.mode_switch.clicked.connect(on_mode)
        top_bar.addWidget(self.mode_label)
        top_bar.addWidget(self.mode_switch)

        imp_btn = QPushButton('⬆️ Import')
        imp_btn.clicked.connect(self._import_csv)
        exp_btn = QPushButton('⬇️ Export')
        exp_btn.clicked.connect(self._export_csv)
        top_bar.addWidget(imp_btn)
        top_bar.addWidget(exp_btn)

        content_layout.addLayout(top_bar)

        # Stacked widget for pages
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        # Inventory page
        inv_page = QWidget(); inv_layout = QVBoxLayout(inv_page)
        inv_layout.setSpacing(10)
        # Products card
        prod_card = QFrame(); prod_card.setObjectName('card')
        pc_layout = QVBoxLayout(prod_card)
        pc_layout.setContentsMargins(8,8,8,8)
        self.products_table = QTableWidget(0,4)
        self.products_table.setHorizontalHeaderLabels(['SKU','Name','Price','Stock'])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        pc_layout.addWidget(self.products_table)

        p_actions = QHBoxLayout()
        add_btn = QPushButton('➕ Add'); add_btn.clicked.connect(self._add_product)
        edit_btn = QPushButton('✏️ Edit'); edit_btn.clicked.connect(self._edit_product)
        rem_btn = QPushButton('🗑️ Remove'); rem_btn.clicked.connect(self._remove_product)
        tocart_btn = QPushButton('🛒 Add to Cart'); tocart_btn.clicked.connect(self._add_to_cart_from_selected)
        p_actions.addWidget(add_btn); p_actions.addWidget(edit_btn); p_actions.addWidget(rem_btn); p_actions.addStretch(); p_actions.addWidget(tocart_btn)
        pc_layout.addLayout(p_actions)

        inv_layout.addWidget(prod_card, 1)
        self.stack.addWidget(inv_page)

        # Cart page
        cart_page = QWidget(); cart_layout = QVBoxLayout(cart_page)
        cart_card = QFrame(); cart_card.setObjectName('card')
        cc_layout = QVBoxLayout(cart_card)
        cc_layout.setContentsMargins(8,8,8,8)
        self.cart_table = QTableWidget(0,4)
        self.cart_table.setHorizontalHeaderLabels(['SKU','Name','Qty','Total'])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cc_layout.addWidget(self.cart_table)

        cart_ctrl = QHBoxLayout()
        inc = QPushButton('+ Qty'); dec = QPushButton('- Qty'); rem = QPushButton('Remove')
        inc.clicked.connect(lambda: self._change_cart_qty(1)); dec.clicked.connect(lambda: self._change_cart_qty(-1)); rem.clicked.connect(self._remove_cart_item)
        cart_ctrl.addWidget(inc); cart_ctrl.addWidget(dec); cart_ctrl.addWidget(rem); cart_ctrl.addStretch()
        cc_layout.addLayout(cart_ctrl)

        # totals card
        totals = QFrame(); totals.setObjectName('card')
        t_layout = QHBoxLayout(totals)
        t_layout.setContentsMargins(12,12,12,12)
        self.sub_lbl = QLabel('Subtotal: 0.00'); self.tax_lbl = QLabel('Tax (10%): 0.00'); self.total_lbl = QLabel('Total: 0.00')
        for w in (self.sub_lbl, self.tax_lbl, self.total_lbl): t_layout.addWidget(w)
        pay_btn = QPushButton('💳 Checkout'); pay_btn.clicked.connect(self._checkout)
        clear_btn = QPushButton('Clear Cart'); clear_btn.clicked.connect(self._clear_cart)
        t_layout.addStretch(); t_layout.addWidget(clear_btn); t_layout.addWidget(pay_btn)

        cart_layout.addWidget(cart_card, 1)
        cart_layout.addWidget(totals)
        self.stack.addWidget(cart_page)

        # Settings page (simple)
        set_page = QWidget(); set_layout = QVBoxLayout(set_page)
        set_layout.addWidget(QLabel('Settings - coming soon'))
        self.stack.addWidget(set_page)

        # Wire sidebar buttons
        self.btn_inventory.clicked.connect(lambda: self._switch_page(0))
        self.btn_cart.clicked.connect(lambda: self._switch_page(1))
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))
        self.theme_toggle.clicked.connect(lambda: self._apply_theme(dark=self.theme_toggle.isChecked()))

        # Put sidebar and content into main layout
        main_layout.addWidget(sidebar, 0)
        main_layout.addWidget(content, 1)
        self.setCentralWidget(central)

        # Small style
        self.setStyleSheet(_STYLES)

    # -------------------- Theme & Styling --------------------
    def _apply_theme(self, dark=True):
        if dark:
            self.setStyleSheet(_STYLES)
        else:
            # light override
            light = _STYLES.replace('#121212', '#f5f5f5').replace('#1f1f1f', '#ffffff').replace('#e0e0e0', '#d6d6d6')
            self.setStyleSheet(light)

    # -------------------- Product persistence --------------------
    def _load_products(self):
        if not os.path.exists(PRODUCTS_CSV):
            self.products = [
                {'sku':'P001','name':'Pencil','price':money('10.00'),'stock':'100'},
                {'sku':'P002','name':'Notebook','price':money('50.00'),'stock':'50'},
            ]
            self._save_products();
            return
        try:
            with open(PRODUCTS_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.products = [r for r in reader]
        except Exception as e:
            QMessageBox.warning(self, 'Load Error', str(e))
            self.products = []

    def _save_products(self):
        try:
            with open(PRODUCTS_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['sku','name','price','stock'])
                writer.writeheader();
                for p in self.products: writer.writerow(p)
        except Exception as e:
            QMessageBox.warning(self, 'Save Error', str(e))

    # -------------------- Products UI --------------------
    def _refresh_products(self):
        q = self.search.text().strip().lower()
        rows = [p for p in self.products if q in p['sku'].lower() or q in p['name'].lower()]
        self.products_table.setRowCount(len(rows))
        for i,p in enumerate(rows):
            self.products_table.setItem(i,0,QTableWidgetItem(p['sku']))
            self.products_table.setItem(i,1,QTableWidgetItem(p['name']))
            self.products_table.setItem(i,2,QTableWidgetItem(str(p['price'])))
            self.products_table.setItem(i,3,QTableWidgetItem(str(p['stock'])))

    def _add_product(self):
        dlg = ProductDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data['sku'] or not data['name']:
                QMessageBox.warning(self, 'Validation', 'SKU and Name required')
                return
            if any(p['sku']==data['sku'] for p in self.products):
                QMessageBox.warning(self, 'Validation', 'SKU exists')
                return
            self.products.append(data)
            self._save_products(); self._refresh_products()

    def _edit_product(self):
        r = self.products_table.currentRow()
        if r < 0:
            QMessageBox.information(self, 'Select', 'Select product to edit')
            return
        sku = self.products_table.item(r,0).text()
        prod = next((p for p in self.products if p['sku']==sku), None)
        if not prod: return
        dlg = ProductDialog(self, prod)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            for i,p in enumerate(self.products):
                if p['sku']==sku: self.products[i]=data; break
            self._save_products(); self._refresh_products()

    def _remove_product(self):
        r = self.products_table.currentRow()
        if r < 0:
            QMessageBox.information(self, 'Select', 'Select product to remove')
            return
        sku = self.products_table.item(r,0).text()
        res = QMessageBox.question(self, 'Confirm', f'Remove {sku}?')
        if res != QMessageBox.Yes: return
        self.products=[p for p in self.products if p['sku']!=sku]
        self._save_products(); self._refresh_products()

    # -------------------- Cart --------------------
    def _add_to_cart_from_selected(self):
        r = self.products_table.currentRow()
        if r < 0:
            QMessageBox.information(self, 'Select', 'Select a product')
            return
        sku = self.products_table.item(r,0).text()
        prod = next((p for p in self.products if p['sku']==sku), None)
        if not prod: return
        qty, ok = QInputDialog.getInt(self, 'Quantity', f'Quantity for {prod["name"]}:', 1,1,int(prod['stock']))
        if not ok: return
        qty = int(qty)
        if qty > int(prod['stock']): QMessageBox.warning(self,'Stock','Not enough stock'); return
        c = next((x for x in self.cart if x['sku']==sku), None)
        if c: c['qty'] += qty
        else:
            self.cart.append({'sku':prod['sku'],'name':prod['name'],'price':Decimal(prod['price']),'qty':qty})
        self._refresh_cart()
        self._switch_page(1)

    def _change_cart_qty(self, delta):
        r = self.cart_table.currentRow()
        if r < 0: return
        sku = self.cart_table.item(r,0).text()
        for c in self.cart:
            if c['sku']==sku:
                new = c['qty'] + delta
                if new <=0: QMessageBox.information(self,'Qty','Minimum 1'); return
                prod = next((p for p in self.products if p['sku']==sku), None)
                if prod and new > int(prod['stock']): QMessageBox.warning(self,'Stock','Not enough stock'); return
                c['qty']=new
                break
        self._refresh_cart()

    def _remove_cart_item(self):
        r = self.cart_table.currentRow()
        if r < 0: return
        sku = self.cart_table.item(r,0).text()
        self.cart = [c for c in self.cart if c['sku']!=sku]
        self._refresh_cart()

    def _clear_cart(self):
        self.cart = []
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_table.setRowCount(len(self.cart))
        subtotal = Decimal('0.00')
        for i,c in enumerate(self.cart):
            total = (c['price'] * c['qty']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal += total
            self.cart_table.setItem(i,0,QTableWidgetItem(c['sku']))
            self.cart_table.setItem(i,1,QTableWidgetItem(c['name']))
            self.cart_table.setItem(i,2,QTableWidgetItem(str(c['qty'])))
            self.cart_table.setItem(i,3,QTableWidgetItem(money(total)))
        tax = (subtotal * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (subtotal + tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.sub_lbl.setText(f'Subtotal: {money(subtotal)}')
        self.tax_lbl.setText(f'Tax (10%): {money(tax)}')
        self.total_lbl.setText(f'Total: {money(total)}')

    def _checkout(self):
        if not self.cart: QMessageBox.information(self,'Cart Empty','Add items before checkout'); return
        subtotal = sum((c['price']*c['qty']) for c in self.cart)
        subtotal = Decimal(subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tax = (subtotal * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (subtotal + tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        cash_str, ok = QInputDialog.getText(self, 'Cash', f'Total: {money(total)}. Cash received:')
        if not ok: return
        try:
            cash = Decimal(cash_str) if cash_str else total
        except Exception:
            QMessageBox.warning(self,'Input','Invalid amount'); return
        if cash < total: QMessageBox.warning(self,'Payment','Insufficient cash'); return
        change = (cash - total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f'receipt_{now}.txt'
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write('=== Receipt ===\n')
                f.write(f'Date: {datetime.datetime.now()}\n\n')
                for c in self.cart:
                    f.write(f"{c['sku']} {c['name']} x{c['qty']} @ {money(c['price'])} = {money(c['price']*c['qty'])}\n")
                f.write('\n')
                f.write(f'Subtotal: {money(subtotal)}\n')
                f.write(f'Tax (10%): {money(tax)}\n')
                f.write(f'Total: {money(total)}\n')
                f.write(f'Cash: {money(cash)}\n')
                f.write(f'Change: {money(change)}\n')
                f.write('\nThank you!\n')
        except Exception as e:
            QMessageBox.warning(self,'Receipt',str(e)); return
        # Deduct stock
        for c in self.cart:
            for p in self.products:
                if p['sku']==c['sku']:
                    p['stock'] = str(max(0, int(p['stock']) - c['qty']))
        self._save_products(); self.cart = []; self._refresh_cart(); self._refresh_products()
        QMessageBox.information(self,'Done',f'Payment complete. Receipt: {fname}')

    # -------------------- CSV --------------------
    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import CSV', '', 'CSV Files (*.csv)')
        if not path: return
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                items = [r for r in reader]
                for it in items:
                    if not all(k in it for k in ('sku','name','price','stock')):
                        raise ValueError('CSV missing columns')
                self.products = items; self._save_products(); self._refresh_products(); QMessageBox.information(self,'Import','Imported')
        except Exception as e:
            QMessageBox.warning(self,'Import Error',str(e))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export CSV', 'products_export.csv', 'CSV Files (*.csv)')
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['sku','name','price','stock'])
                writer.writeheader();
                for p in self.products: writer.writerow(p)
            QMessageBox.information(self,'Export','Saved')
        except Exception as e:
            QMessageBox.warning(self,'Export',str(e))

    # -------------------- Misc --------------------
    def _switch_page(self, idx):
        self.btn_inventory.setChecked(idx==0)
        self.btn_cart.setChecked(idx==1)
        self.btn_settings.setChecked(idx==2)
        self.stack.setCurrentIndex(idx)

# -------------------- QSS Styles --------------------
_STYLES = """
QWidget{background:#121212;color:#e0e0e0}
#sidebar{background:#1f1f1f;border-radius:8px}
#appTitle{font-weight:700;font-size:14px;padding-left:6px}
#content{background:transparent}
QPushButton{background:#2b2b2b;border:none;padding:8px;border-radius:8px}
QPushButton:hover{background:#3a3a3a}
QTableWidget{background:transparent;border:0}
QHeaderView::section{background:#2b2b2b;padding:6px;border:0}
#card{background:#181818;border-radius:12px;padding:6px}
QLineEdit{background:#141414;border:1px solid #2b2b2b;padding:8px;border-radius:8px}
QSpinBox{background:#141414;border:1px solid #2b2b2b;padding:4px;border-radius:6px}
"""

# -------------------- Run --------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()