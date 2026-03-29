from flask import Flask, render_template, request
import random
import math

app = Flask(__name__)

# ============ EXISTING LOGIC (DO NOT MODIFY) ============

# Crop database with shelf life and base prices
CROP_DATA = {
    'tomato': {'shelf_life_days': 14, 'base_price': 25, 'perishable': True},
    'potato': {'shelf_life_days': 60, 'base_price': 15, 'perishable': False},
    'onion': {'shelf_life_days': 45, 'base_price': 20, 'perishable': False},
    'spinach': {'shelf_life_days': 7, 'base_price': 30, 'perishable': True},
    'carrot': {'shelf_life_days': 30, 'base_price': 35, 'perishable': False},
    'cabbage': {'shelf_life_days': 21, 'base_price': 18, 'perishable': False},
}

def simulate_temperature():
    """Simulate current storage temperature"""
    return round(random.uniform(15, 35), 1)

def calculate_freshness(crop_type, time_since_harvest, temperature):
    """Calculate freshness/quality based on time and temperature"""
    if crop_type not in CROP_DATA:
        return 0

    shelf_life = CROP_DATA[crop_type]['shelf_life_days']
    perishable = CROP_DATA[crop_type]['perishable']

    # Temperature factor: higher temp = faster decay
    temp_factor = 1.0
    if temperature > 25:
        temp_factor = 1 + (temperature - 25) * 0.05 if perishable else 1 + (temperature - 25) * 0.02

    # Effective time with temperature impact
    effective_time = time_since_harvest * temp_factor

    # Calculate freshness (exponential decay)
    freshness = max(0, 100 * math.exp(-effective_time / shelf_life))
    return round(freshness, 1)

def get_market_data(crop_type):
    """Get predefined market data (current + past prices)"""
    base_price = CROP_DATA.get(crop_type, {'base_price': 20})['base_price']

    # Generate past prices with some variation
    past_prices = []
    for i in range(7):
        variation = random.uniform(-0.15, 0.15)
        past_prices.append(round(base_price * (1 + variation), 2))

    # Current price with variation
    current_price = round(base_price * random.uniform(0.85, 1.15), 2)

    return {
        'past_prices': past_prices,
        'current_price': current_price,
        'base_price': base_price
    }

def detect_trend_and_estimate(past_prices):
    """Detect price trend and estimate future price"""
    if len(past_prices) < 2:
        return 'stable', past_prices[0] if past_prices else 0

    # Simple linear trend
    changes = [past_prices[i+1] - past_prices[i] for i in range(len(past_prices)-1)]
    avg_change = sum(changes) / len(changes)

    if avg_change > 0.5:
        trend = 'rising'
    elif avg_change < -0.5:
        trend = 'falling'
    else:
        trend = 'stable'

    # Estimate future price (next day)
    future_price = past_prices[-1] + avg_change
    future_price = max(future_price, 0)

    return trend, round(future_price, 2)

def make_decision(freshness, current_price, future_price, trend):
    """Decide: Sell Now or Wait"""
    if freshness < 30:
        return 'Sell Now', 'Low freshness - sell immediately'

    if trend == 'rising' and freshness > 50:
        return 'Wait', 'Price rising, good freshness - wait for better price'

    if trend == 'falling':
        return 'Sell Now', 'Price falling - sell before further drop'

    if future_price > current_price * 1.05 and freshness > 60:
        return 'Wait', 'Expected price increase with sufficient shelf life'

    return 'Sell Now', 'Current conditions favorable for selling'

def calculate_gain_loss(current_price, future_price, decision):
    """Calculate potential gain/loss"""
    if decision == 'Wait':
        gain = future_price - current_price
    else:
        gain = 0  # Selling now, no change

    percentage = (gain / current_price * 100) if current_price > 0 else 0
    return round(gain, 2), round(percentage, 1)

# ============ NEW FEATURE: SMART MANDI SELECTION ============

# Sample mandis with distance and price variation
MANDIS = [
    {'name': 'Local Mandi', 'distance': 5, 'price_factor': 1.0},
    {'name': 'City Market', 'distance': 15, 'price_factor': 1.1},
    {'name': 'Wholesale Hub', 'distance': 30, 'price_factor': 1.25},
    {'name': 'District Mandi', 'distance': 45, 'price_factor': 1.15},
    {'name': 'Regional Market', 'distance': 60, 'price_factor': 1.3},
]

def calculate_travel_time(distance):
    """Calculate travel time: distance / 10 (in hours)"""
    return distance / 10

def calculate_quality_after_travel(initial_quality, travel_time, crop_type):
    """Reduce quality based on travel time"""
    # Perishable crops lose more quality during transport
    perishable = CROP_DATA.get(crop_type, {}).get('perishable', False)

    if perishable:
        quality_loss_rate = 3  # 3% per hour for perishable
    else:
        quality_loss_rate = 1  # 1% per hour for non-perishable

    quality_loss = travel_time * quality_loss_rate
    final_quality = max(0, initial_quality - quality_loss)
    return round(final_quality, 1)

def smart_mandi_selection(crop_type, freshness, market_data):
    """Select best mandi based on final value"""
    current_price = market_data['current_price']

    results = []
    for mandi in MANDIS:
        # Calculate travel time
        travel_time = calculate_travel_time(mandi['distance'])

        # Calculate quality after travel
        quality_after_travel = calculate_quality_after_travel(
            freshness, travel_time, crop_type
        )

        # Calculate price at this mandi
        mandi_price = current_price * mandi['price_factor']

        # Calculate final value: price × quality_after_travel
        # Quality is expressed as percentage (0-100)
        final_value = mandi_price * (quality_after_travel / 100)

        results.append({
            'name': mandi['name'],
            'distance': mandi['distance'],
            'travel_time': travel_time,
            'quality_after_travel': quality_after_travel,
            'mandi_price': round(mandi_price, 2),
            'final_value': round(final_value, 2)
        })

    # Select mandi with highest final_value
    best_mandi = max(results, key=lambda x: x['final_value'])

    return results, best_mandi

# ============ FLASK ROUTES ============


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    mandi_results = None
    best_mandi = None

    if request.method == 'POST':
        crop_type = request.form.get('crop_type', '').lower()
        time_since_harvest = float(request.form.get('time_since_harvest', 0))

        if crop_type in CROP_DATA:
            # Existing logic
            temperature = simulate_temperature()
            freshness = calculate_freshness(crop_type, time_since_harvest, temperature)
            market_data = get_market_data(crop_type)
            trend, future_price = detect_trend_and_estimate(market_data['past_prices'])
            decision, reason = make_decision(freshness, market_data['current_price'], future_price, trend)
            gain, percentage = calculate_gain_loss(market_data['current_price'], future_price, decision)

            # New feature: Smart Mandi Selection
            mandi_results, best_mandi = smart_mandi_selection(crop_type, freshness, market_data)

            result = {
                'crop_type': crop_type.title(),
                'time_since_harvest': time_since_harvest,
                'temperature': temperature,
                'freshness': freshness,
                'current_price': market_data['current_price'],
                'past_prices': market_data['past_prices'],
                'trend': trend,
                'future_price': future_price,
                'decision': decision,
                'reason': reason,
                'gain': gain,
                'percentage': percentage
            }
        else:
            result = {'error': f"Unknown crop type: {crop_type}"}

    return render_template('index.html',
                          crops=list(CROP_DATA.keys()),
                          result=result,
                          mandi_results=mandi_results,
                          best_mandi=best_mandi)


@app.route('/crop-health', methods=['GET', 'POST'])
def crop_health():
    """Crop Health Monitoring page"""
    result = None
    weather_rec = None

    # Sample weather data
    weather_conditions = [
        {'temp': 28, 'condition': 'Sunny', 'humidity': 65},
        {'temp': 32, 'condition': 'Hot', 'humidity': 45},
        {'temp': 24, 'condition': 'Cloudy', 'humidity': 80},
    ]
    current_weather = random.choice(weather_conditions)

    if request.method == 'POST':
        crop_type = request.form.get('crop_type', '').lower()
        leaf_condition = request.form.get('leaf_condition', 'healthy_green')
        pest_presence = request.form.get('pest_presence', 'none')
        soil_moisture = request.form.get('soil_moisture', 'optimal')
        growth_stage = request.form.get('growth_stage', 'vegetative')

        if crop_type in CROP_DATA:
            # Calculate health score based on inputs
            health_score = 100

            # Leaf condition impact
            leaf_penalties = {
                'healthy_green': 0,
                'slight_yellowing': -10,
                'significant_yellowing': -25,
                'spots_present': -20,
                'wilting': -30,
                'dried_edges': -15
            }
            health_score += leaf_penalties.get(leaf_condition, 0)

            # Pest presence impact
            pest_penalties = {
                'none': 0,
                'few_visible': -10,
                'moderate': -25,
                'severe': -40
            }
            health_score += pest_penalties.get(pest_presence, 0)

            # Soil moisture impact
            moisture_penalties = {
                'optimal': 0,
                'slightly_dry': -10,
                'very_dry': -20,
                'waterlogged': -25
            }
            health_score += moisture_penalties.get(soil_moisture, 0)

            health_score = max(0, min(100, health_score))

            # Determine status
            if health_score >= 80:
                status = 'Excellent'
            elif health_score >= 60:
                status = 'Good'
            elif health_score >= 40:
                status = 'Fair'
            elif health_score >= 20:
                status = 'Poor'
            else:
                status = 'Critical'

            # Generate issues and recommendations
            issues = []
            recommendations = []

            if leaf_condition != 'healthy_green':
                issues.append(f'Leaf condition: {leaf_condition.replace("_", " ").title()}')
                recommendations.append('Inspect leaves regularly and consider foliar spray')

            if pest_presence != 'none':
                issues.append(f'Pest infestation: {pest_presence.replace("_", " ").title()}')
                recommendations.append('Apply appropriate pesticide or neem oil')

            if soil_moisture == 'very_dry':
                issues.append('Soil moisture critically low')
                recommendations.append('Increase irrigation frequency')
            elif soil_moisture == 'waterlogged':
                issues.append('Soil waterlogged - risk of root rot')
                recommendations.append('Improve drainage and reduce watering')

            if not issues:
                issues.append('No significant issues detected')

            if not recommendations:
                recommendations.append('Continue current best practices')

            # Weather-based recommendations
            weather_rec = {
                'current_temp': current_weather['temp'],
                'condition': current_weather['condition'],
                'recommended_crops': ['tomato', 'cabbage'] if current_weather['temp'] < 30 else ['onion', 'potato'],
                'avoid_crops': ['spinach'] if current_weather['temp'] > 28 else [],
                'general_advice': 'Water early morning to reduce evaporation' if current_weather['temp'] > 28 else 'Optimal conditions for most crops'
            }

            result = {
                'crop_type': crop_type.title(),
                'leaf_condition': leaf_condition.replace('_', ' ').title(),
                'pest_presence': pest_presence.replace('_', ' ').title(),
                'soil_moisture': soil_moisture.replace('_', ' ').title(),
                'growth_stage': growth_stage.title(),
                'health': {
                    'health_score': health_score,
                    'status': status,
                    'issues': issues,
                    'recommendations': recommendations
                }
            }
        else:
            result = {'error': f"Unknown crop type: {crop_type}"}

    return render_template('crop_health.html',
                          crops=list(CROP_DATA.keys()),
                          result=result,
                          weather_rec=weather_rec,
                          farmer_name='Farmer')


@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@app.route('/logout')
def logout():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)