# bitpulse.paypal

This project is a FastAPI-based backend application that manages fixed monthly subscriptions using PayPal for payment processing. It provides a simple API for creating, managing, and processing subscriptions.

## Features

- Create and manage fixed monthly subscriptions
- Integration with PayPal for payment processing
- MongoDB for data storage
- FastAPI for efficient API development

## Project Structure

```
subscription_service/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── subscription.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── subscription.py
│   ├── crud/
│   │   ├── __init__.py
│   │   └── subscription.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   └── subscription.py
│   │   └── routes.py
│   └── services/
│       ├── __init__.py
│       └── paypal.py
├── tests/
│   ├── __init__.py
│   └── test_subscription.py
├── .env
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository:

   ```
   git clone <repository-url>
   cd subscription_service
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with the following content:
   ```
   MONGODB_URL=your_mongodb_url
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   PAYPAL_MODE=sandbox
   SUBSCRIPTION_PRICE=19.99
   SUBSCRIPTION_NAME=My Website Subscription
   ```
   Replace the placeholder values with your actual MongoDB and PayPal credentials.

## Running the Application

To run the application, use the following command:

```
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

- `POST /subscriptions/`: Create a new subscription
- `GET /subscriptions/{subscription_id}`: Get details of a specific subscription
- `PUT /subscriptions/{subscription_id}`: Update a subscription
- `DELETE /subscriptions/{subscription_id}`: Delete a subscription
- `POST /subscriptions/{subscription_id}/execute`: Execute a PayPal agreement to activate a subscription

## Usage

1. Create a new subscription:

   ```
   POST /subscriptions/
   {
     "user_id": "user123"
   }
   ```

2. The API will return a response with the subscription details and a PayPal approval URL. Redirect the user to this URL to approve the subscription.

3. After the user approves the subscription, execute the agreement:

   ```
   POST /subscriptions/{subscription_id}/execute
   {
     "token": "paypal_token_from_approval_url"
   }
   ```

4. The subscription will be activated, and you can manage it using the other endpoints.

## Testing

To run the tests, use the following command:

```
pytest
```

## Configuration

The application uses environment variables for configuration. These can be set in the `.env` file or as system environment variables. The available configuration options are:

- `MONGODB_URL`: The URL for your MongoDB instance
- `PAYPAL_CLIENT_ID`: Your PayPal client ID
- `PAYPAL_CLIENT_SECRET`: Your PayPal client secret
- `PAYPAL_MODE`: The PayPal mode (sandbox or live)
- `SUBSCRIPTION_PRICE`: The price of the subscription
- `SUBSCRIPTION_NAME`: The name of the subscription

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
