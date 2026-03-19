from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import re

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user TEXT, 
                       note TEXT, 
                       amt REAL, 
                       cat TEXT, 
                       date TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS reminders 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user TEXT, 
                       title TEXT, 
                       amt REAL, 
                       due_date TEXT, 
                       status TEXT DEFAULT 'pending')''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS splits 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user TEXT, 
                       expense_id INTEGER, 
                       note TEXT, 
                       total_amt REAL, 
                       split_with TEXT, 
                       your_share REAL, 
                       date TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS streaks 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user TEXT, 
                       date TEXT, 
                       daily_budget REAL, 
                       daily_spent REAL, 
                       under_budget INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS sms_transactions 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user TEXT, 
                       sms_text TEXT, 
                       parsed_amt REAL, 
                       parsed_type TEXT, 
                       date TEXT, 
                       added_to_expenses INTEGER DEFAULT 0)''')
    

    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_expense():
    data = request.json
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO expenses (user, note, amt, cat, date) VALUES (?, ?, ?, ?, ?)',
                   (data['user'], data['note'], data['amt'], data['cat'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/get_all/<email>')
def get_expenses(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, note, amt, cat, date FROM expenses WHERE user = ? ORDER BY date DESC', (email,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "note": r[1], "amt": r[2], "cat": r[3], "date": r[4]} for r in rows])

@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_expense(id):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route('/download/<email>')
def download_expenses(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, note, cat, amt FROM expenses WHERE user = ? ORDER BY date DESC', (email,))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Description', 'Category', 'Amount (₹)'])
    writer.writerows(rows)
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=SpendWise_Report_{email}.csv"}
    )

@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    data = request.json
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO reminders (user, title, amt, due_date, status) VALUES (?, ?, ?, ?, ?)',
                   (data['user'], data['title'], data['amt'], data['due_date'], 'pending'))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/get_reminders/<email>')
def get_reminders(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, amt, due_date, status FROM reminders WHERE user = ? ORDER BY due_date ASC', (email,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "title": r[1], "amt": r[2], "due_date": r[3], "status": r[4]} for r in rows])

@app.route('/mark_reminder/<int:id>', methods=['PUT'])
def mark_reminder(id):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE reminders SET status = ? WHERE id = ?', ('paid', id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})

@app.route('/add_split', methods=['POST'])
def add_split():
    data = request.json
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO splits (user, note, total_amt, split_with, your_share, date) VALUES (?, ?, ?, ?, ?, ?)',
                   (data['user'], data['note'], data['total_amt'], data['split_with'], data['your_share'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/get_splits/<email>')
def get_splits(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, note, total_amt, split_with, your_share, date FROM splits WHERE user = ? ORDER BY date DESC', (email,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "note": r[1], "total_amt": r[2], "split_with": r[3], "your_share": r[4], "date": r[5]} for r in rows])

@app.route('/get_insights/<email>')
def get_insights(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT SUM(amt) FROM expenses WHERE user = ? AND date LIKE ? AND cat != "Income"', (email, f'{current_month}%'))
    current_total = cursor.fetchone()[0] or 0
    
    prev_month_date = datetime.now().replace(day=1)
    if prev_month_date.month == 1:
        prev_month = f'{prev_month_date.year - 1}-12'
    else:
        prev_month = f'{prev_month_date.year}-{str(prev_month_date.month - 1).zfill(2)}'
    
    cursor.execute('SELECT SUM(amt) FROM expenses WHERE user = ? AND date LIKE ? AND cat != "Income"', (email, f'{prev_month}%'))
    prev_total = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT cat, SUM(amt) as total FROM expenses WHERE user = ? AND cat != "Income" GROUP BY cat ORDER BY total DESC LIMIT 1', (email,))
    top_cat = cursor.fetchone()
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    cursor.execute('SELECT date, SUM(amt) as daily_total FROM expenses WHERE user = ? AND cat != "Income" AND date >= ? GROUP BY date ORDER BY date DESC', (email, thirty_days_ago))
    daily_spending = cursor.fetchall()
    
    conn.close()
    
    insights = []
    anomalies = []
    
    if prev_total > 0:
        change = ((current_total - prev_total) / prev_total) * 100
        if change > 0:
            insights.append(f"You spent {abs(change):.0f}% more this month (₹{current_total:.0f} vs ₹{prev_total:.0f})")
        else:
            insights.append(f"Great! You saved {abs(change):.0f}% this month (₹{current_total:.0f} vs ₹{prev_total:.0f})")
    
    if top_cat:
        insights.append(f"Your highest spending is on {top_cat[0]} (₹{top_cat[1]:.0f})")
    
    if current_total > 0:
        daily_avg = current_total / datetime.now().day
        insights.append(f"Your daily average spending is ₹{daily_avg:.0f}")
    
    if len(daily_spending) >= 7:
        amounts = [day[1] for day in daily_spending]
        avg_spending = sum(amounts) / len(amounts)
        std_dev = (sum((x - avg_spending) ** 2 for x in amounts) / len(amounts)) ** 0.5
        threshold = avg_spending + (2 * std_dev)
        
        for date, amount in daily_spending[:7]:
            if amount > threshold and amount > avg_spending * 2:
                anomalies.append({
                    "date": date,
                    "amount": amount,
                    "avg": avg_spending,
                    "message": f"⚠️ Unusual spending on {date}: ₹{amount:.0f} (Your avg: ₹{avg_spending:.0f})"
                })
    
    return jsonify({"insights": insights, "anomalies": anomalies})

@app.route('/get_predictions/<email>')
def get_predictions(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m')
    cursor.execute('SELECT strftime("%Y-%m", date) as month, SUM(amt) as total FROM expenses WHERE user = ? AND cat != "Income" AND date >= ? GROUP BY month ORDER BY month DESC LIMIT 3', (email, three_months_ago + '-01'))
    monthly_data = cursor.fetchall()
    
    conn.close()
    
    if len(monthly_data) >= 2:
        amounts = [m[1] for m in monthly_data]
        avg_spending = sum(amounts) / len(amounts)
        
        if len(amounts) >= 3:
            trend = (amounts[0] - amounts[-1]) / len(amounts)
            predicted = avg_spending + trend
        else:
            predicted = avg_spending
        
        return jsonify({
            "predicted_amount": round(predicted, 2),
            "avg_last_3_months": round(avg_spending, 2),
            "trend": "increasing" if predicted > avg_spending else "decreasing"
        })
    
    return jsonify({"predicted_amount": 0, "avg_last_3_months": 0, "trend": "neutral"})

@app.route('/generate_pdf/<email>')
def generate_pdf(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    
    from datetime import datetime
    current_month = datetime.now().strftime('%Y-%m')
    
    cursor.execute('SELECT date, note, cat, amt FROM expenses WHERE user = ? AND date LIKE ? ORDER BY date DESC', (email, f'{current_month}%'))
    transactions = cursor.fetchall()
    
    cursor.execute('SELECT SUM(amt) FROM expenses WHERE user = ? AND date LIKE ? AND cat = "Income"', (email, f'{current_month}%'))
    total_income = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(amt) FROM expenses WHERE user = ? AND date LIKE ? AND cat != "Income"', (email, f'{current_month}%'))
    total_expense = cursor.fetchone()[0] or 0
    
    conn.close()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title = Paragraph(f"<b>SpendWise Monthly Report - {datetime.now().strftime('%B %Y')}</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    summary_data = [
        ['Summary', 'Amount'],
        ['Total Income', f'₹{total_income:.2f}'],
        ['Total Expenses', f'₹{total_expense:.2f}'],
        ['Balance', f'₹{(total_income - total_expense):.2f}']
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*inch))
    
    trans_title = Paragraph("<b>Transactions</b>", styles['Heading2'])
    elements.append(trans_title)
    elements.append(Spacer(1, 0.2*inch))
    
    trans_data = [['Date', 'Description', 'Category', 'Amount']]
    for t in transactions:
        trans_data.append([t[0], t[1][:30], t[2], f'₹{t[3]:.2f}'])
    
    trans_table = Table(trans_data, colWidths=[1.2*inch, 2.5*inch, 1.3*inch, 1*inch])
    trans_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    elements.append(trans_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=SpendWise_Report_{current_month}.pdf'}
    )

@app.route('/get_streaks/<email>')
def get_streaks(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    cursor.execute('SELECT date, SUM(amt) as daily_total FROM expenses WHERE user = ? AND cat != "Income" AND date >= ? GROUP BY date ORDER BY date DESC', (email, thirty_days_ago))
    daily_spending = cursor.fetchall()
    
    conn.close()
    
    if not daily_spending:
        return jsonify({"current_streak": 0, "best_streak": 0, "daily_budget": 500})
    
    amounts = [d[1] for d in daily_spending]
    daily_budget = sum(amounts) / len(amounts) if amounts else 500
    
    current_streak = 0
    best_streak = 0
    temp_streak = 0
    
    for date, amount in daily_spending:
        if amount <= daily_budget:
            temp_streak += 1
            best_streak = max(best_streak, temp_streak)
        else:
            temp_streak = 0
    
    for date, amount in daily_spending:
        if amount <= daily_budget:
            current_streak += 1
        else:
            break
    
    return jsonify({
        "current_streak": current_streak,
        "best_streak": best_streak,
        "daily_budget": round(daily_budget, 2)
    })

@app.route('/parse_sms', methods=['POST'])
def parse_sms():
    data = request.json
    sms_text = data.get('sms_text', '')
    user = data.get('user')
    
    sms_lower = sms_text.lower()
    amount = None
    trans_type = None
    category = None
    
    debited_pos = sms_lower.find('debited')
    credited_pos = sms_lower.find('credited')
    
    if debited_pos != -1 and (credited_pos == -1 or debited_pos < credited_pos):
        debited_match = re.search(r'debited[^0-9]*([0-9,]+(?:\.\d{2})?)', sms_lower)
        if debited_match:
            amount = float(debited_match.group(1).replace(',', ''))
            trans_type = "Expense"
            if any(word in sms_lower for word in ['swiggy', 'zomato', 'restaurant', 'food', 'cafe', 'hotel']):
                category = "Food"
            elif any(word in sms_lower for word in ['uber', 'ola', 'petrol', 'fuel', 'transport', 'taxi', 'auto']):
                category = "Transport"
            elif any(word in sms_lower for word in ['electricity', 'bill', 'recharge', 'water', 'internet', 'phone']):
                category = "Bills"
            elif any(word in sms_lower for word in ['amazon', 'flipkart', 'shopping', 'mall', 'store']):
                category = "Shopping"
            else:
                category = "Others"
    elif credited_pos != -1:
        credited_match = re.search(r'credited[^0-9]*([0-9,]+(?:\.\d{2})?)', sms_lower)
        if credited_match:
            amount = float(credited_match.group(1).replace(',', ''))
            trans_type = "Income"
            category = "Income"
    
    if not amount or not trans_type:
        return jsonify({"status": "error", "message": "Could not find 'debited' or 'credited' in SMS"})
    
    from datetime import datetime
    date = datetime.now().strftime('%Y-%m-%d')
    
    merchant_match = re.search(r'at\s+([A-Z\s]+)', sms_text)
    note = merchant_match.group(1).strip() if merchant_match else f"SMS {trans_type}"
    
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO sms_transactions (user, sms_text, parsed_amt, parsed_type, date) VALUES (?, ?, ?, ?, ?)',
                   (user, sms_text, amount, trans_type, date))
    
    cursor.execute('INSERT INTO expenses (user, note, amt, cat, date) VALUES (?, ?, ?, ?, ?)',
                   (user, note, amount, category, date))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "amount": amount,
        "type": trans_type,
        "category": category,
        "note": note
    })

@app.route('/get_sms_history/<email>')
def get_sms_history(email):
    conn = sqlite3.connect('expense_tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, parsed_amt, parsed_type, date FROM sms_transactions WHERE user = ? ORDER BY date DESC', (email,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "amount": r[1], "type": r[2], "date": r[3]} for r in rows])

if __name__ == '__main__':
    app.run(debug=True)


