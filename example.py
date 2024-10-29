
import mysql.connector
import json
import csv
from decimal import Decimal

ui_inputs = { 
        "planning_scenario": "Public places",
        "years_of_analysis": [1,2,3],
        "Ai": 50,
        "Li": 1500,
        "Bipc": .25,
        "Birate": 3.5,
        "Eg": 5.5,
        "backoff_factor":1,
        "cabling_cost": 500000,
        "capex_2W": 2500,
        "capex_3WS": 112000,
        "capex_4WS": 250000,
        "capex_4WF": 1500000,
        "hoarding cost": 900000,
        "kiosk_cost": 180000,
        "year1_conversion": 0.02,
        "year2_conversion": 0.05,
        "year3_conversion": 0.1,
        "holiday_percentage": 0.3,
        "fast_charging": 0.3,
        "slow_charging": 0.15,
        "cluster": True,
        "cluster_th": 0.02,
    "plot_dendrogram": True
}




idSelect=int(input("Which id?\t"))
query="SELECT * FROM analysis_inputs WHERE id = %s;"

mydb = mysql.connector.connect(
  host="139.59.23.75",
  port=5782,
  user="dbadminusr",
  password="$D3vel0per2024",
  database="EVCI"
)

mycursor = mydb.cursor()


mycursor.execute(query,(idSelect,))



column_names = [i[0] for i in mycursor.description]
results = [
    {**dict(zip(column_names, row)), "plot_dendrogram": "true"} 
    for row in mycursor.fetchall()
]

db_input=results[0]

for key, value in db_input.items():
    if isinstance(value, Decimal):
        db_input[key] = float(value)
    elif key == "years_of_analysis":  
        db_input[key] = list(range(1,value+1))

for key in ui_inputs:
    if key in db_input:
        ui_inputs[key] = db_input[key]
# Write data to CSV
print(ui_inputs)
mycursor.close()
mydb.close()

from evci_tool.analysis import *

analysis = analyze_sites('abc124','panaji',ui_inputs)
# json_object = json.dumps(analysis, indent = 4) 
print(analysis)
