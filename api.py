from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from decimal import Decimal
from evci_tool.analysis import analyze_sites
import json
import pandas as pd

app = FastAPI()

# Pydantic model to define input structure
class AnalyzeRequest(BaseModel):
    id: int

# Default UI inputs
ui_inputs = { 
    "planning_scenario": "Public places",
    "years_of_analysis": [1, 2, 3],
    "Ai": 50,
    "Li": 1500,
    "Bipc": .25,
    "Birate": 3.5,
    "Eg": 5.5,
    "backoff_factor": 1,
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

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    idSelect = request.id

    # Database connection and query
    query = "SELECT * FROM analysis_inputs WHERE id = %s;"
    mydb = mysql.connector.connect(
        host="139.59.23.75",
        port=5782,
        user="dbadminusr",
        password="$D3vel0per2024",
        database="EVCI"
    )
    mycursor = mydb.cursor()
    mycursor.execute(query, (idSelect,))

    # Retrieve column names and data
    column_names = [i[0] for i in mycursor.description]
    results = [{**dict(zip(column_names, row)), "plot_dendrogram": "true"} for row in mycursor.fetchall()]

    if not results:
        mycursor.close()
        mydb.close()
        raise HTTPException(status_code=404, detail="No data found for given ID")

    db_input = results[0]

    # Close database connection
    mycursor.close()
    mydb.close()

    # Format db_input for compatibility
    for key, value in db_input.items():
        if isinstance(value, Decimal):
            db_input[key] = float(value)
        elif key == "years_of_analysis":  
            db_input[key] = list(range(1, value + 1))

    # Override defaults with database values if present
    for key in ui_inputs:
        if key in db_input:
            ui_inputs[key] = db_input[key]

    # Run analysis
    analysis = analyze_sites('abc124', 'panaji', ui_inputs)

    df1 = analysis['opportunity_charging']['initial']

    df1.to_csv('data/output/opportunity_initial.csv', index=False) 

    df1 = pd.read_csv('data/output/opportunity_initial.csv')  # Replace 'data.csv' with your file path

    df2 = analysis['destination_charging']['initial']
    df2.to_csv('data/output/destination_initial.csv', index=False) 
    df2 = pd.read_csv('data/output/destination_initial.csv')
    df3 = analysis['destination_charging']['cluster']
    df3.to_csv('data/output/destination_cluster.csv', index=False)
    df3 = pd.read_csv('data/output/destination_cluster.csv')

# Convert DataFrame to JSON
    json_data1 = df1.to_json(orient='records', indent=4)
    json_data2 = df2.to_json(orient='records', indent=4)
    json_data3 = df3.to_json(orient='records', indent=4)

    # Return JSON response
    return json_data1,json_data2,json_data3
