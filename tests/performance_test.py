import requests 
import time 

# This URL should be the ngrok URL when running locally, or the production URL
url = "http://localhost:8000/ivr/welcome"

def load_test(num_requests=50):
    print(f"Starting load test with {num_requests} requests to {url}...")
    start_time = time.time()
    success = 0
    
    for i in range(num_requests):
        try:
            # Twilio webhook uses POST
            res = requests.post(url)
            if res.status_code == 200:
                success += 1
        except Exception as e:
            print(f"Request failed: {e}")
            
    total_time = time.time() - start_time
    
    # Fixed f-string bugs from the Module 4 notes
    print(f"Sent {num_requests} requests, {success} successful.")
    if num_requests > 0:
        print(f"Average response time: {total_time / num_requests:.2f} seconds")

if __name__ == "__main__":
    load_test(50)
