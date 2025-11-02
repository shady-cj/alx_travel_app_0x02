"""
Script to test the complete payment flow
Run this script to simulate a payment process
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"
EMAIL = "john.doe@example.com"
PASSWORD = "password123"

def print_section(title):
    """Print section header"""
    print("\n" + "="*50)
    print(f"  {title}")
    print("="*50 + "\n")

def print_response(response):
    """Print formatted response"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def main():
    session = requests.Session()
    
    # Step 1: Register or Login
    print_section("Step 1: User Authentication")
    
    # Try to login
    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    
    print(f"Logging in as: {EMAIL}")
    # Note: You'll need to implement login endpoint or use Django session auth
    # For now, we'll assume authentication is handled
    
    # Step 2: Get Available Listings
    print_section("Step 2: Browse Available Listings")
    
    response = session.get(f"{BASE_URL}/listings/")
    print_response(response)
    
    if response.status_code == 200:
        listings = response.json()
        if listings:
            selected_listing = listings[0]['property_id']
            print(f"\nSelected Listing: {listings[0]['name']}")
            print(f"Price per night: {listings[0]['price_per_night']}")
        else:
            print("No listings available. Please seed the database.")
            return
    else:
        print("Failed to fetch listings")
        return
    
    # Step 3: Create a Booking
    print_section("Step 3: Create Booking")
    
    booking_data = {
        "property_id": selected_listing,
        "start_date": "2025-12-01",
        "end_date": "2025-12-05"
    }
    
    print(f"Creating booking with data:\n{json.dumps(booking_data, indent=2)}")
    response = session.post(
        f"{BASE_URL}/bookings/",
        json=booking_data,
        headers={"Content-Type": "application/json"}
    )
    print_response(response)
    
    if response.status_code == 201:
        booking = response.json()
        booking_id = booking['booking_id']
        total_price = booking['total_price']
        print(f"\n✓ Booking created successfully!")
        print(f"Booking ID: {booking_id}")
        print(f"Total Price: {total_price}")
    else:
        print("Failed to create booking")
        return
    
    # Step 4: Initiate Payment
    print_section("Step 4: Initiate Payment")
    
    payment_data = {
        "booking_id": booking_id
    }
    
    print(f"Initiating payment for booking: {booking_id}")
    response = session.post(
        f"{BASE_URL}/payments/initiate/",
        json=payment_data,
        headers={"Content-Type": "application/json"}
    )
    print_response(response)
    
    if response.status_code == 201:
        payment_response = response.json()
        tx_ref = payment_response['tx_ref']
        checkout_url = payment_response['checkout_url']
        payment_id = payment_response['payment_id']
        
        print(f"\n✓ Payment initiated successfully!")
        print(f"Payment ID: {payment_id}")
        print(f"Transaction Ref: {tx_ref}")
        print(f"\nCheckout URL: {checkout_url}")
        print("\n⚠ Please visit the checkout URL to complete payment")
        print("After completing payment, press Enter to verify...")
        input()
        
        # Step 5: Verify Payment
        print_section("Step 5: Verify Payment")
        
        print(f"Verifying payment: {tx_ref}")
        response = session.get(f"{BASE_URL}/payments/verify/{tx_ref}/")
        print_response(response)
        
        if response.status_code == 200:
            verification = response.json()
            payment_status = verification['payment']['payment_status']
            
            print(f"\n✓ Payment verification completed!")
            print(f"Status: {payment_status}")
            
            if payment_status == 'completed':
                print("\n🎉 Payment successful! Booking confirmed!")
            elif payment_status == 'pending':
                print("\n⏳ Payment is still pending...")
            else:
                print(f"\n❌ Payment failed with status: {payment_status}")
        else:
            print("Failed to verify payment")
        
        # Step 6: Get Payment Details
        print_section("Step 6: Get Payment Details")
        
        response = session.get(f"{BASE_URL}/payments/{payment_id}/")
        print_response(response)
        
    else:
        print("Failed to initiate payment")
        return
    
    print_section("Test Completed")
    print("Check your email for confirmation (if configured)")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ALX Travel App - Payment Flow Test")
    print("="*50)
    print("\nPrerequisites:")
    print("1. Django server is running (python manage.py runserver)")
    print("2. Database is seeded with data (python manage.py seed)")
    print("3. Celery worker is running (celery -A alx_travel_app worker)")
    print("4. Redis is running")
    print("5. Chapa API keys are configured in .env")
    print("\nStarting test in 3 seconds...")
    time.sleep(3)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        import traceback
        traceback.print_exc()