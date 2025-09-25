import pandas as pd
from flask import Flask, jsonify, render_template, request
from scipy import stats
import numpy as np

app = Flask(__name__)

WOD_CONFIG = {
    'fran': {'name': 'Fran', 'type': 'time', 'unit': 's', 'min': 100, 'max': 600, 'category': 'Benchmarks'},
    'helen': {'name': 'Helen', 'type': 'time', 'unit': 's', 'min': 360, 'max': 900, 'category': 'Benchmarks'},
    'grace': {'name': 'Grace', 'type': 'time', 'unit': 's', 'min': 60, 'max': 480, 'category': 'Benchmarks'},
    'filthy50': {'name': 'Filthy Fifty', 'type': 'time', 'unit': 's', 'min': 900, 'max': 2400, 'category': 'Benchmarks'},
    'fgonebad': {'name': 'Fight Gone Bad', 'type': 'reps', 'unit': 'reps', 'min': 150, 'max': 500, 'category': 'Benchmarks'},
    'run400': {'name': '400m Run', 'type': 'time', 'unit': 's', 'min': 50, 'max': 120, 'category': 'Running'},
    'run5k': {'name': '5k Run', 'type': 'time', 'unit': 's', 'min': 900, 'max': 2400, 'category': 'Running'},
    'candj': {'name': 'Clean & Jerk', 'type': 'weight', 'unit': 'lbs', 'min': 100, 'max': 400, 'category': 'Strength'},
    'snatch': {'name': 'Snatch', 'type': 'weight', 'unit': 'lbs', 'min': 80, 'max': 315, 'category': 'Strength'},
    'deadlift': {'name': 'Deadlift', 'type': 'weight', 'unit': 'lbs', 'min': 150, 'max': 600, 'category': 'Strength'},
    'backsq': {'name': 'Back Squat', 'type': 'weight', 'unit': 'lbs', 'min': 120, 'max': 550, 'category': 'Strength'},
}

def load_and_clean_data(wod_name, config):
    try:
        df = pd.read_csv('crossfit_data.csv')
        raw_scores = pd.to_numeric(df[wod_name], errors='coerce').dropna()
        min_val, max_val = config.get('min'), config.get('max')
        return raw_scores[(raw_scores >= min_val) & (raw_scores <= max_val)]
    except (FileNotFoundError, KeyError):
        return pd.Series(dtype=float)

all_wod_data = {wod: load_and_clean_data(wod, cfg) for wod, cfg in WOD_CONFIG.items()}

def format_value(value, wod_type):
    if wod_type == 'time':
        minutes = int(value // 60)
        seconds = int(value % 60)
        return f"{minutes}:{seconds:02d}"
    return str(round(value, 1))

@app.route("/")
def home():
    return render_template('index.html', wod_config=WOD_CONFIG)

@app.route("/api/wod/<string:wod_name>/percentile", methods=['POST'])
def wod_percentile(wod_name):
    if wod_name not in WOD_CONFIG:
        return jsonify({"error": "Workout not found."}), 404
    config = WOD_CONFIG[wod_name]
    scores = all_wod_data[wod_name]
    if scores.empty:
        return jsonify({"error": f"No valid data for '{config['name']}'."}), 500
    user_score = float(request.get_json().get('score', 0))
    if user_score <= 0:
        return jsonify({"error": "Invalid score provided."}), 400
    if config['type'] == 'time':
        percentile = 100 - stats.percentileofscore(scores, user_score, kind='strict')
    else:
        percentile = stats.percentileofscore(scores, user_score, kind='strict')
    
    bins = np.linspace(config['min'], config['max'], 11)
    counts, bin_edges = np.histogram(scores, bins=bins)
    chart_labels = [f"{format_value(edge, config['type'])} - {format_value(bin_edges[i+1], config['type'])}" for i, edge in enumerate(bin_edges[:-1])]
    chart_data = [int(c) for c in counts]
    return jsonify({
        "user_score": user_score,
        "percentile": round(percentile),
        "config": config,
        "chart_labels": chart_labels,
        "chart_data": chart_data
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)