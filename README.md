# My Dockerized Application

This repository contains the Docker configuration and source code for my application.

## Overview

This application is composed of several services, each running in its own Docker container:

- **app**: Python Flask web service
- **mongo**: MongoDB database
- **sql_server**: Microsoft SQL Server database
- **redis**: Redis caching server

## Usage

To run the application locally using Docker, follow these steps:

1. Install images from docker hub:
https://hub.docker.com/repository/docker/nafets2002/my-app-image/general.

or just clone this repository:

    ```
    git clone https://github.com/nafets2002stefan/PAD_FINAL.git
    ```

2. Navigate to the repository directory:

    ```bash
    cd your-repo
    ```

3. Build the Docker images:

    ```bash
    docker-compose build
    ```

4. Start the services:

    ```bash
    docker-compose up
    ```

5. Access the application in your web browser at [http://localhost:5003](http://localhost:5003).

6. There are a lot of endpoints(8).Where you can see in Postman collection.
    IMPORTANT!!! First time running app, initialize DB, make GET request  http://localhost:5003/initialize

    After that, we have GET,POST /products, PUT /products/id
    and GET,POST /items, PUT /items/id
    And the last method which is a transaction:
    POST for /transaction.