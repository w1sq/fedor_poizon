# Fedor Poizon

Fedor Poizon is a Telegram bot that facilitates ordering items from Poizon, a popular Chinese e-commerce platform specializing in streetwear and sneakers. This bot provides a streamlined interface for users to request specific items they want to purchase from Poizon.

## Features

-   Custom order requests: Users can specify the exact item they want to order from Poizon.
-   Order management: Place orders and track order status.
-   User profiles: Manage personal information and shipping addresses.
-   Admin panel: Process order requests, update order statuses, and handle customer inquiries.
-   Simple interface: Easy-to-use commands for placing orders and checking status.

This bot simplifies the process of ordering specific items from Poizon for international customers. It acts as an intermediary, allowing users to request items they've found on Poizon's platform without needing to navigate the Chinese website or app directly.

The bot doesn't provide a browsable catalog or direct integration with Poizon's inventory. Instead, it focuses on facilitating custom orders based on user requests, streamlining the ordering process for specific items users have already identified on Poizon.

## Prerequisites

-   Docker
-   Docker Compose (optional, for easier management)

## Docker Setup and Usage

1. Clone the repository:

    ```
    git clone https://github.com/w1sq/fedor_poizon.git
    cd fedor_poizon
    ```

2. Create a `config.py` file in the root directory with your configuration:

    ```python
    class Config:
        TGBOT_API_KEY = "your_telegram_bot_api_key"
        HOST = "db"  # This should match the service name in docker-compose.yml
        PORT = "5432"
        LOGIN = "your_db_login"
        PASSWORD = "your_db_password"
        DATABASE = "your_db_name"
    ```

3. Build and run the Docker container:

    ```
    docker build -t fedor_poizon .
    docker run -d --name fedor_poizon_container fedor_poizon
    ```

    Alternatively, if you're using Docker Compose, create a `docker-compose.yml` file:

    ```yaml
    version: "3"
    services:
        bot:
            build: .
            depends_on:
                - db
        db:
            image: postgres:13
            environment:
                POSTGRES_DB: your_db_name
                POSTGRES_USER: your_db_login
                POSTGRES_PASSWORD: your_db_password
    ```

    Then run:

    ```
    docker-compose up -d
    ```

The bot will initialize the database and start running in the container.

## Project Structure

-   `bot/`: Contains the main bot logic
-   `db/`: Database-related code
    -   `storage/`: User and Order storage classes
-   `utils/`: Utility functions
-   `main.py`: Entry point of the application
-   `config.py`: Configuration file (not tracked by git)
-   `requirements.txt`: List of Python dependencies
-   `Dockerfile`: For containerizing the application

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
