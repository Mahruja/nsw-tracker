import json
import boto3
from datetime import datetime, timedelta
import uuid
import random

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('TransportData')

def lambda_handler(event, context):
    """
    Main Lambda function to process transport data
    This function is triggered every 30 seconds via CloudWatch Events
    """
    
    try:
        # Determine the type of request
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/transport')
        
        if http_method == 'GET' and '/transport' in path:
            return get_transport_data(event)
        elif http_method == 'POST' and '/update' in path:
            return update_transport_data(event)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
                },
                'body': json.dumps({'error': 'Invalid endpoint'})
            }
            
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_transport_data(event):
    """
    Retrieve transport data from DynamoDB and return predictions
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        location = query_params.get('location', 'sydney')
        transport_type = query_params.get('type', 'all')
        
        # Scan DynamoDB for recent transport data
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('timestamp').gt(
                int((datetime.now() - timedelta(minutes=5)).timestamp())
            )
        )
        
        transport_items = response.get('Items', [])
        
        # Apply ML prediction logic (simplified for MVP)
        predicted_data = []
        for item in transport_items:
            prediction = apply_ml_prediction(item)
            
            # Filter by transport type if specified
            if transport_type != 'all' and item.get('type') != transport_type:
                continue
                
            predicted_data.append(prediction)
        
        # Sort by predicted arrival time
        predicted_data.sort(key=lambda x: x.get('predicted_arrival_mins', 999))
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'data': predicted_data[:10],  # Return top 10 results
                'timestamp': datetime.now().isoformat(),
                'location': location
            })
        }
        
    except Exception as e:
        print(f"Error in get_transport_data: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Failed to retrieve transport data'})
        }

def update_transport_data(event):
    """
    Update transport data from Transport NSW API
    This function runs every 30 seconds via scheduled CloudWatch Events
    """
    try:
        # In real implementation, this would call Transport NSW Open Data API
        # For MVP demo, we'll generate sample data
        
        sample_transport_data = generate_sample_data()
        
        # Store each transport item in DynamoDB
        for item in sample_transport_data:
            table.put_item(Item=item)
        
        print(f"Successfully updated {len(sample_transport_data)} transport records")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'updated_records': len(sample_transport_data),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error in update_transport_data: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Failed to update transport data'})
        }

def apply_ml_prediction(transport_item):
    """
    Apply machine learning prediction algorithm
    In real implementation, this would use SageMaker endpoints
    """
    
    # Get base arrival time from timetable
    base_arrival = transport_item.get('scheduled_arrival_mins', 10)
    
    # Factors for ML prediction (simplified)
    time_of_day_factor = get_time_of_day_factor()
    traffic_factor = get_traffic_factor()
    weather_factor = get_weather_factor()
    historical_delay_factor = get_historical_delay_factor(transport_item)
    
    # Calculate predicted arrival time
    predicted_delay = (
        time_of_day_factor * 0.3 +
        traffic_factor * 0.4 +
        weather_factor * 0.1 +
        historical_delay_factor * 0.2
    )
    
    predicted_arrival = max(1, int(base_arrival + predicted_delay))
    
    # Calculate confidence score
    confidence = calculate_confidence_score(transport_item, predicted_delay)
    
    return {
        'id': transport_item.get('id'),
        'type': transport_item.get('type'),
        'route': transport_item.get('route'),
        'destination': transport_item.get('destination'),
        'current_location': transport_item.get('current_location'),
        'predicted_arrival_mins': predicted_arrival,
        'predicted_arrival_text': f"{predicted_arrival} mins" if predicted_arrival > 1 else "1 min",
        'confidence_score': confidence,
        'confidence_text': f"{confidence}%",
        'delay_mins': predicted_arrival - base_arrival,
        'timestamp': datetime.now().isoformat()
    }

def get_time_of_day_factor():
    """Calculate delay factor based on time of day"""
    current_hour = datetime.now().hour
    
    # Peak hours have higher delays
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        return random.uniform(2, 5)  # Peak hour delays
    elif 6 <= current_hour <= 22:
        return random.uniform(0, 2)  # Normal day delays
    else:
        return random.uniform(-1, 1)  # Off-peak (early/negative delays possible)

def get_traffic_factor():
    """Get traffic factor (would integrate with Google Maps API)"""
    # Simulate traffic conditions
    return random.uniform(-1, 3)

def get_weather_factor():
    """Get weather factor (would integrate with Bureau of Meteorology API)"""
    # Simulate weather impact
    weather_conditions = ['clear', 'rain', 'storm', 'fog']
    condition = random.choice(weather_conditions)
    
    weather_impact = {
        'clear': 0,
        'rain': 1.5,
        'storm': 3,
        'fog': 2
    }
    
    return weather_impact.get(condition, 0)

def get_historical_delay_factor(transport_item):
    """Calculate historical delay factor for this route"""
    # In real implementation, this would query historical data from DynamoDB
    route = transport_item.get('route', '')
    
    # Simulate historical delay patterns
    if 'train' in transport_item.get('type', ''):
        return random.uniform(-0.5, 1.5)  # Trains generally more reliable
    else:
        return random.uniform(0, 2.5)  # Buses more variable

def calculate_confidence_score(transport_item, predicted_delay):
    """Calculate confidence score for the prediction"""
    
    # Base confidence
    confidence = 90
    
    # Reduce confidence for larger delays
    if abs(predicted_delay) > 5:
        confidence -= 15
    elif abs(predicted_delay) > 2:
        confidence -= 8
    
    # Adjust based on transport type
    if transport_item.get('type') == 'train':
        confidence += 5  # Trains more predictable
    
    # Random variation
    confidence += random.uniform(-5, 5)
    
    return max(70, min(98, int(confidence)))

def generate_sample_data():
    """Generate sample transport data for demo purposes"""
    
    routes = [
        {'type': 'bus', 'route': '380', 'destination': 'Circular Quay'},
        {'type': 'bus', 'route': '391', 'destination': 'Coogee Beach'},
        {'type': 'bus', 'route': '400', 'destination': 'Bondi Junction'},
        {'type': 'train', 'route': 'T4 Eastern Suburbs', 'destination': 'Central'},
        {'type': 'train', 'route': 'T2 Inner West', 'destination': 'Parramatta'},
        {'type': 'light-rail', 'route': 'L1 Dulwich Hill', 'destination': 'Central'},
    ]
    
    locations = [
        'Bondi Junction', 'Randwick', 'Central Station', 'Town Hall',
        'Circular Quay', 'Wynyard', 'Martin Place', 'Kings Cross'
    ]
    
    sample_data = []
    
    for i in range(20):
        route_info = random.choice(routes)
        
        item = {
            'id': f"{route_info['type'][0].upper()}{str(i+1).zfill(3)}",
            'type': route_info['type'],
            'route': route_info['route'],
            'destination': route_info['destination'],
            'current_location': random.choice(locations),
            'scheduled_arrival_mins': random.randint(1, 15),
            'timestamp': int(datetime.now().timestamp()),
            'last_updated': datetime.now().isoformat()
        }
        
        sample_data.append(item)
    
    return sample_data

# For scheduled execution (CloudWatch Events trigger)
def scheduled_update(event, context):
    """
    Function triggered by CloudWatch Events every 30 seconds
    """
    try:
        # Call the update function
        update_event = {
            'httpMethod': 'POST',
            'path': '/update'
        }
        
        result = update_transport_data(update_event)
        print(f"Scheduled update completed: {result}")
        
        return result
        
    except Exception as e:
        print(f"Error in scheduled_update: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Scheduled update failed'})
        }