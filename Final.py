'''
This model is to be considered a possible way of how a transaction between two companies can be automatized.
The model has many simplifications and it is supposed to run on blockchain.
 To get a better understand of how it works, it is supposed to read the theoretical part first where all parts are explained.
 All code is based on a buyer's point of view.
 In order to make it work, you should download first the database "Final project.db" and the Excel sheet "buyers_balance_sheet"
'''

# used to implement all BC system
import sqlite3
# used to import today's date and time
from datetime import datetime
# used to work with excel
import openpyxl
# used to generate BC signatures
import random
import shutil
from supporting_function import *

# to connect to the database
conn = sqlite3.connect('Final Project.db')
cur = conn.cursor()


# function which allows to insert data in any table by passing the name of it
def insert_table_data(table):
    # taking today's date and time
    date = str(datetime.today())
    headers = list()
    items = list()
    table_data = cur.execute('''SELECT * FROM ''' + table)
    # appending all headers to the list 'headers'
    for el in table_data.description:
        headers.append(el[0])
        # appending all items passed by the user corresponding to headers above to the list 'items'
        if el[0] == 'Date':
            items.append(date)
        elif el[0] == 'InvoiceID':
            invoice_id = input(f'insert {el[0]}: ')
            items.append(invoice_id)
        elif el[0] == 'Seller_signature':
            seller_signature = random.randint(100, 1000)
            items.append(seller_signature)
        elif el[0] == 'Buyer_signature':
            buyer_signature = random.randint(100, 1000)
            items.append(buyer_signature)
        else:
            data = input(f'insert {el[0]}: ')
            items.append(data)
    sql = '''INSERT INTO ''' + table + '''(''' + ','.join(headers) + ''') VALUES(''' + ','.join('?'*len(headers)) + ''')'''
    cur.execute(sql, items)
    conn.commit()
    # once we create an invoice automatically it's supposed to take data from the smart contract
    if table == 'Invoice':
        bp_headers = []
        data = cur.execute('''SELECT * FROM Blockchain_phases''')
        for el in data.description:
            bp_headers.append(el[0])
        sql = '''INSERT INTO Blockchain_phases(''' + ','.join(bp_headers) + ''') VALUES(''' +\
              ','.join('?'*len(bp_headers)) + ''')'''
        items = [invoice_id, random.randint(1000, 100000)]
        remaining_items = len(headers) - 1
        for el in range(remaining_items):
            items.append('No')
        cur.execute(sql, items)
        conn.commit()
    else:
        pass

    return table + ' successfully recorded'


# checks if there is enough money and blocks it
def buyer_bank_account(invoice_id):
    amounts = []
    headers = []
    data = []
    # get today's date and time
    time = str(datetime.today())
    transactions = cur.execute("SELECT * FROM Account_balance")
    rows = transactions.fetchall()
    for row in rows:
        # appending all amount to calculate buyer's balance
        amounts.append(row[5])
        # getting last transaction id
        last_transaction = row[0]
    # appending all headers in 'headers'
    for row in transactions.description:
        headers.append(row[0])

    invoice_cost = cur.execute("SELECT * FROM Invoice WHERE InvoiceID =?", str(invoice_id))
    row = invoice_cost.fetchall()
    # getting invoice amount
    total_amount = row[0][4]
    # verifying there are enough money to afford it
    if sum(amounts) > total_amount:
        sql = '''INSERT INTO Account_balance(''' + ','.join(headers) + ''') VALUES('''\
              + ','.join('?'*len(headers)) + ''')'''
        # getting all data needed but keep the table modifiable
        for header in headers:
            if header == 'Description':
                data.append(row[0][5])
            elif header == 'TransactionID':
                data.append(last_transaction+1)
            elif header == 'SellerVAT':
                data.append(row[0][3])
            elif header == 'Date':
                data.append(time)
            elif header == 'Amount':
                data.append(-total_amount)
            elif header == 'InvoiceID':
                data.append(invoice_id)
            else:
                item = input(f'insert {header}: ')
                data.append(item)
        cur.execute(sql, data)
        conn.commit()
        # change bank_transaction value in bc_phases
        updated_data = '''UPDATE Blockchain_phases SET Bank_transaction = ''' + str(total_amount) \
                       + ''' WHERE InvoiceID = ''' + str(invoice_id)
        cur.execute(updated_data)
        conn.commit()
    else:
        return "Buyer's account has not enough money"
    return "Buyer's account has enough money"


# Confirms it was shipped
def seller_shipment(invoice_id):
    answer = input('Has goods been shipped? (Y/N) ')
    if answer == 'Y':
        # Inserting date & time goods are shipped
        updated_data = '''UPDATE Blockchain_phases SET Seller_shipment = datetime('now', 'localtime') ''' \
                           + ''' WHERE InvoiceID = ''' + str(invoice_id)
        cur.execute(updated_data)
        conn.commit()
    else:
        return 'Something went wrong'
    return 'Seller has sent goods'


# confirm it was arrived and everything was ok
def buyer_confirmation(invoice_id):
    # Same as above
    answer = input('Has goods been arrived? (Y/N) ')
    if answer == 'Y':
        updated_data = '''UPDATE Blockchain_phases SET Buyer_confirmation = datetime('now', 'localtime')
        WHERE InvoiceID = ''' + str(invoice_id)
        cur.execute(updated_data)
        conn.commit()
    else:
        return 'Something went wrong'
    return 'Buyer confirmed that everything went good'
# shipper could do it



# updating party scores
def update_score(seller_vat, buyer_vat):
    old_score = cur.execute("SELECT * FROM Participants")
    rows = old_score.fetchall()
    # Re-asking parties if everything went as expected
    response = input('Do you both confirm that everything went good so far? (Y/N) ')
    if response == 'Y':
        # if so, adding 1 point to both parties
        for row in rows:
            if row[0] == seller_vat:
                new_seller_score = row[3] + 1
            elif row[0] == buyer_vat:
                new_buyer_score = row[3] + 1
            else:
                pass
    else:
        # if not, differencing 10 points
        for row in rows:
            if row[0] == seller_vat:
                new_seller_score = row[3] - 10
            elif row[0] == buyer_vat:
                new_buyer_score = row[3] - 10
            else:
                return "party doesn't exist"

    # updating buyer & seller's score
    update_buyer_score = "UPDATE Participants SET Score = " + str(new_buyer_score) \
                         + " WHERE VATNumber = " + str(buyer_vat)
    cur.execute(update_buyer_score)
    conn.commit()
    update_seller_score = "UPDATE Participants SET Score = " + str(new_seller_score) \
                          + " WHERE VATNumber = " + str(seller_vat)
    cur.execute(update_seller_score)
    conn.commit()
    return 'Score has been updated successfully'


# paying VAT to the state and the seller
def paying_account_transaction(invoice_id):
    vat_perc = int(input("What's the VAT? (%)  "))
    time = str(datetime.today())
    invoice_cost = cur.execute("SELECT * FROM Invoice WHERE InvoiceID =?",  str(invoice_id))
    row = invoice_cost.fetchall()
    total_amount = row[0][4]
    net_amount = total_amount/(1+vat_perc/100)
    tax_amount = total_amount - net_amount
    updated_data = '''UPDATE Blockchain_phases SET Bank_account_transfert = datetime('now', 'localtime') ''' \
                   + ''' WHERE InvoiceID = ''' + str(invoice_id)
    cur.execute(updated_data)
    conn.commit()

    data = [invoice_id, time, str(vat_perc), str(tax_amount)]
    sql = '''INSERT INTO VAT(TransactionID,Date,VAT,Amount) VALUES(?,?,?,?)'''
    cur.execute(sql, data)
    conn.commit()
    tax_rounnded = round(tax_amount, 2)
    net_amount_rounded = round(net_amount, 2)
    return 'Paid ' + str(tax_rounnded) + '$ to the state and ' + str(net_amount_rounded) + '$ to the seller'


# recording DeA to the public ledger and, in the case of an asset, update asset table
def public_ledger(invoice_id):
    # asking seller credit and buyer debit (it is supposed to use budget items which can be found in the financial statements)
    buyer_debit = str(input("What is the buyer's debit?  "))
    assets = str(input('Is it an asset?(Y/N) '))
    cur.execute('SELECT COUNT(*) from Asset_IDs')
    cur_result = cur.fetchone()
    asset_id = cur_result[0] + 1
    if assets == 'Y':
        items = [asset_id, buyer_debit, invoice_id]
        sql = '''INSERT INTO Asset_IDs(Asset_ID, Name, Invoice_ID) VALUES(?,?,?)'''
        cur.execute(sql, items)
        conn.commit()
    else:
        pass
    seller_credit = str(input("What is the seller's credit?  "))
    time = str(datetime.today())
    invoice_cost = cur.execute("SELECT * FROM Invoice WHERE InvoiceID =?", str(invoice_id))
    row = invoice_cost.fetchall()
    total_amount = row[0][4]
    # recording all items needed
    items = [invoice_id, time, buyer_debit, seller_credit, total_amount]
    sql = '''INSERT INTO Public_ledger(InvoiceID, Date, Buyer_debit, Seller_credit, Amount) VALUES(?,?,?,?,?)'''
    cur.execute(sql, items)
    conn.commit()
    return 'Credit/Debits successfully recorded to Public Ledger'


# recording transaction on buyer's private ledger knowing its credit
def buyer_ledger(invoice_id):
    time = str(datetime.today())
    buyer_credit = str(input("What is the buyer's credit?  "))
    pvt_ledger = cur.execute("SELECT * FROM Public_ledger WHERE InvoiceID =?", str(invoice_id))
    row = pvt_ledger.fetchall()
    buyer_debit = row[0][2]
    total_amount = row[0][4]
    # recording all items needed (not keeping it modifiable because I knew database headers from the beginning)
    items = [invoice_id, time, buyer_debit, buyer_credit, total_amount]
    sql = '''INSERT INTO Private_ledger(InvoiceID, Date, Credit, Debit, Amount) VALUES(?,?,?,?,?)'''
    cur.execute(sql, items)
    conn.commit()
    return "Credit/Debits successfully recorded to Buyer's Ledger"


# updating assets once they are bought
def update_first_details(invoice_id):
    time = datetime.today()
    invoice_items = cur.execute("SELECT * FROM Invoice WHERE InvoiceID = " + str(invoice_id))
    rows = invoice_items.fetchall()
    for row in rows:
        paid_value = row[4]
        bought_date = row[1]

    asset_ids = cur.execute("SELECT Asset_ID FROM Asset_IDs WHERE Invoice_ID = " + str(invoice_id))
    asset_id = asset_ids.fetchone()[0]
    amortisation_years = str(input('Is the asset amortisable? If so, how many years does it last? (if not == N) '))
    if amortisation_years == 'N':
        annual_amortisation = 0
    else:
        annual_amortisation = int(paid_value)/int(amortisation_years)

    rev = str(input('Is the asset revaluation/(depretation)? If so, how much? (if not == N) '))
    if rev == 'N':
        tot_rev = 0
    else:
        tot_rev = rev

    final_value  = paid_value - tot_rev
    tot_amortisation = 0
    items = [asset_id, bought_date, time, paid_value, annual_amortisation, tot_amortisation, tot_rev, final_value]
    sql = '''INSERT INTO Balance_sheet_details(AssetID, Bought_date, Updated_date, Paid_value, Annual_amortisation, 
    Total_current_amortisation, Revaluation, Final_value) VALUES(?,?,?,?,?,?,?,?)'''
    cur.execute(sql, items)
    conn.commit()
    return 'Details updated'


# updating assets to state real-time value
def update_details():
    date = datetime.today()
    transactions = cur.execute("SELECT * FROM Balance_sheet_details")
    rows = transactions.fetchall()
    for row in rows:
        bought_date = row[1]
        annual_amortisation = row[4]
        datetime_obj = datetime.strptime(bought_date, '%Y-%m-%d %H:%M:%S')
        total_time = datetime_obj - date
        # Count how many days are passed from the last update
        days = abs(int(str(total_time).split()[0]))
        tot_amortisation = annual_amortisation * (days / 365)
        final_value = row[5] - tot_amortisation
        updated_data = '''UPDATE Balance_sheet_details SET Updated_date = ''' + str(date) + \
                       ''', Total_current_amortisation = ''' + tot_amortisation + ''', Final_value = ''' + final_value \
                       + ''' WHERE AssetID = ''' + str(row[0])
        cur.execute(updated_data)
        conn.commit()
    return 'details updated'


# Exporting excel balance sheet (basically changing the name of pre-defined excel file)
# If you need different format, you can use "journal book" (buyer ledger)
def export_excel_balance_sheet():
    basic_sheet = 'buyers_balance_sheet.xlsx'
    new_name = input('Insert file name: ')
    # Renaming the file
    shutil.copyfile(basic_sheet, new_name)
    return 'Balance sheet exported'


# Updating data in real time when a transaction occurs and/or updating asset amortisations
def update_excel_balance_sheet(invoice_id=0):
    name = input("What's the file name you want to insert data in? ")
    if invoice_id != 0:
        invoice_cost = cur.execute("SELECT * FROM Private_ledger WHERE InvoiceID =?", str(invoice_id))
        row = invoice_cost.fetchall()
        # taking voices from buyer's ledger
        total_amount = int(row[0][4])
        buyer_credit = row[0][3]
        buyer_debit = row[0][2]
        # using a function from a different file
        update_excel_financial_statement(name, total_amount, buyer_credit)
        update_excel_financial_statement(name, total_amount, buyer_debit)
    answer = input('Do you want to insert asset real-time amortisation? (Y/N): ')
    # updating assets through the same process
    if answer == 'Y':
        assets = cur.execute("SELECT * FROM Balance_sheet_details")
        row = assets.fetchall()
        for rows in row:
            print(rows)
            asset_id = rows[0]
            total_amortisation = float(rows[5])
            asset_table = cur.execute("SELECT Name FROM Asset_IDs WHERE Asset_ID =?", str(asset_id))
            asset_name = asset_table.fetchone()
            update_excel_financial_statement(name, total_amortisation, asset_name[0])
        return 'transaction & details updated on excel'
    else:
        return 'transaction updated on excel'

'''
Example(to use as budget items):
Seller's credit:  Vendita merci
Buyer's debit:  Materie prime (att. serv.)
Buyer's credit:  Fornitori terzi Italia
'''
'''
insert_table_data("invoice")
buyer_bank_account(6)
seller_shipment(6)
buyer_confirmation(6)
update_score(101, 102)
paying_account_transaction(6)
public_ledger(6)
buyer_ledger(6)
export_excel_balance_sheet()
update_excel_balance_sheet(6)
'''