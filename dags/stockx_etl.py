from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python import PythonOperator
from azure.storage.blob import ContainerClient
from datetime import datetime, timedelta
import glob
import json
import os
import psycopg2
import requests
from shutil import make_archive
import sys

# AZURE BLOB
container = Variable.get("AZ_BLOB_CONTAINER")
conn_string = Variable.get("AZ_SA_CONN_STRING")

# DATABASE
db_host = Variable.get("DB_HOST")
db_name = Variable.get("DB_NAME")
db_password = Variable.get("DB_PASSWORD")
db_port = Variable.get("DB_PORT")
db_user = Variable.get("DB_USER")


def create_connection():
    "Create Database Connection"

    host = db_host
    dbname = db_name
    user = db_user
    password = db_password
    sslmode = "require"

    # Constructing connection string
    conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(
        host, user, dbname, password, sslmode
    )

    try:
        connection = psycopg2.connect(conn_string)
        print("Connection established")

    except psycopg2.Error as e:
        print(f"Error connecting to Postgres DB : {e}")
        sys.exit(1)

    curr = connection.cursor()

    return connection, curr


def create_table(curr, query):
    "Create Table in Database if it does not exist"
    try:
        curr.execute(query)

    except BaseException as e:
        print(e)


def store_db(curr, query, value):
    "Insert data into Database and commit changes"
    try:
        curr.execute(query, value)

    except BaseException as e:
        print(e)

# GET DATA


def extract():
    try:
        headers = {
            "authority": "stockx.com",
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "origin": "https://www.stockx.com",
            "pragma": "no-cache",
            "sec-ch-ua": '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }

        step = 1

        current_dir = '/app/dags/'
        data_dir = os.path.join(current_dir, "stockx")

        for i in range(1, 26):
            url = f"https://stockx.com/api/browse?&page={i}&_search=nike%20dunk&dataType=product&propsToRetrieve[][]=id&propsToRetrieve[][]=uuid&propsToRetrieve[][]=childId&propsToRetrieve[][]=title&propsToRetrieve[][]=media.thumbUrl&propsToRetrieve[][]=media.smallImageUrl&propsToRetrieve[][]=urlKey&propsToRetrieve[][]=productCategory&propsToRetrieve[][]=releaseDate&propsToRetrieve[][]=market.lowestAsk&propsToRetrieve[][]=market.highestBid&propsToRetrieve[][]=brand&propsToRetrieve[][]=colorway&propsToRetrieve[][]=condition&propsToRetrieve[][]=description&propsToRetrieve[][]=shoe&propsToRetrieve[][]=retailPrice&propsToRetrieve[][]=market.lastSale&propsToRetrieve[][]=market.lastSaleValue&propsToRetrieve[][]=market.lastSaleDate&propsToRetrieve[][]=market.bidAskData&propsToRetrieve[][]=market.changeValue&propsToRetrieve[][]=market.changePercentage&propsToRetrieve[][]=market.salesLastPeriod&propsToRetrieve[][]=market.volatility&propsToRetrieve[][]=market.pricePremium&propsToRetrieve[][]=market.averageDeadstockPrice&propsToRetrieve[][]=market.salesThisPeriod&propsToRetrieve[][]=market.deadstockSold&propsToRetrieve[][]=market.lastHighestBidTime&propsToRetrieve[][]=market.lastLowestAskTime&propsToRetrieve[][]=market.salesInformation&facetsToRetrieve[]=%7B%7D"

            response = requests.get(url, headers=headers)
            result = response.json()

            filename = f"stockx-{datetime.now().strftime('%d-%m-%Y')}-file-{step}.json"

            with open(f"{data_dir}/{filename}", "w", encoding='utf-8') as f:
                json.dump(result, f)

            print(f'Step {step} Done!!!')
            step += 1
    except BaseException as e:
        print(e)

# PROCESS DATA


def transform(file):
    try:
        with open(file, "r") as f:
            data = json.load(f)

        for product in data["Products"]:
            id = product.get("id")
            uuid = product.get("uuid")
            shoe = product.get("shoe")
            title = product.get("title")
            brand = product.get("brand")
            colorway = product.get("colorway")
            condition = product.get("condition")
            description = (
                product.get("description").replace("\n<br>", "").replace("\n", " ")
            )
            product_category = product.get("productCategory")
            release_date = product.get("releaseDate")
            retail_price = product.get("retailPrice")
            lowest_ask = product["market"].get("lowestAsk")
            sales_this_period = product["market"].get("salesThisPeriod")
            sales_last_period = product["market"].get("salesLastPeriod")
            highest_bid = product["market"].get("highestBid")
            volatility = product["market"].get("volatility")
            deadstock_sold = product["market"].get("deadstockSold")
            price_premium = product["market"].get("pricePremium")
            average_deadstock_price = product["market"].get(
                "averageDeadstockPrice")
            last_sale = product["market"].get("lastSale")
            change_value = product["market"].get("changeValue")
            change_percentage = product["market"].get("changePercentage")
            last_lowest_ask_time = product["market"].get("lastLowestAskTime")
            last_highest_bid_time = product["market"].get("lastHighestBidTime")
            last_sale_date = product["market"].get("lastSaleDate")
            url_key = product.get("urlKey")
            small_image_url = product["media"].get("smallImageUrl")
            thumb_url = product["media"].get("thumbUrl")

            yield (
                id,
                uuid,
                shoe,
                title,
                brand,
                colorway,
                condition,
                description,
                product_category,
                release_date,
                retail_price,
                lowest_ask,
                sales_this_period,
                sales_last_period,
                highest_bid,
                volatility,
                deadstock_sold,
                price_premium,
                average_deadstock_price,
                last_sale,
                change_value,
                change_percentage,
                last_lowest_ask_time,
                last_highest_bid_time,
                last_sale_date,
                url_key,
                small_image_url,
                thumb_url,
            )
    except BaseException as e:
        print(e)

# SQL QUERY


create_table_query = """
    CREATE TABLE IF NOT EXISTS stockx (
    date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id VARCHAR(100) NOT NULL,
    uuid VARCHAR(255),
    shoe VARCHAR(255),
    title VARCHAR(255),
    brand VARCHAR(40),
    colorway VARCHAR(100),
    condition VARCHAR(40),
    description VARCHAR(255),
    product_category VARCHAR(100),
    release_date VARCHAR(40),
    retail_price NUMERIC(12, 3),
    lowest_ask NUMERIC(12, 3),
    sales_this_period INTEGER,
    sales_last_period INTEGER,
    highest_bid NUMERIC(12, 3),
    volatility NUMERIC(6, 5),
    deadstock_sold INTEGER,
    price_premium NUMERIC(5, 4),
    average_deadstock_price INTEGER,
    last_sale INTEGER,
    change_value INTEGER,
    change_percentage NUMERIC(8, 7),
    last_lowest_ask_time INTEGER,
    last_highest_bid_time INTEGER,
    last_sale_date VARCHAR(80),
    url_key VARCHAR(120),
    small_image_url VARCHAR(255),
    thumb_url VARCHAR(255)
    )
    """

insert_data_query = """
    INSERT INTO stockx (
        id,
        uuid,
        shoe,
        title,
        brand,
        colorway,
        condition,
        description,
        product_category,
        release_date,
        retail_price,
        lowest_ask,
        sales_this_period,
        sales_last_period,
        highest_bid,
        volatility,
        deadstock_sold,
        price_premium,
        average_deadstock_price,
        last_sale,
        change_value,
        change_percentage,
        last_lowest_ask_time,
        last_highest_bid_time,
        last_sale_date,
        url_key,
        small_image_url,
        thumb_url,
        )
    VALUES (
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s
    )
    """

# STORE DATA


def load():
    try:
        # create database connection
        connection, curr = create_connection()

        # create table if it doesn't exist
        create_table(curr, create_table_query)

        # read in json files in data dir
        files = glob.glob("/app/dags/stockx/*.json")

        for file in files:
            # get data from file
            items = transform(file)

            for value in items:
                # store data in database
                store_db(curr, insert_data_query, value)
                connection.commit()
    except BaseException as e:
        print(e)

    # close cursor and connection
    curr.close()
    connection.close()


def zip_dir():
    make_archive(
        f"/app/dags/stockx-{datetime.now().strftime('%d-%m-%Y')}",
        "zip",
        "/app/dags/stockx/"
    )


def blob_upload():
    try: 
        container_client = ContainerClient.from_connection_string(
            conn_string, container)

        for path in glob.glob("/app/dags/archive/*"):
            print(path)
            file = path.split('/')[-1]
            blob_client = container_client.get_blob_client(file)
            print(blob_client)
            with open(path, "rb") as data:
                blob_client.upload_blob(data)
                print(f"{file} uploaded to blob storage")
    except BaseException as e:
        print(e)


default_args = {
    'owner': 'Deji',
    'retry': 5,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
        default_args=default_args,
        dag_id='stockx_etl',
        start_date=datetime(2022, 9, 17),
        schedule_interval='0 1 * * *') as dag:

    extract_data = PythonOperator(
        task_id='extract_data',
        python_callable=extract
    )

    transform_load = PythonOperator(
        task_id='transform_load',
        python_callable=load
    )

    archive_json_files = PythonOperator(
        task_id='archive_json_files',
        python_callable=zip_dir
    )

    zip_to_archive = BashOperator(
        task_id='zip_to_archive',
        bash_command='mv /app/dags/*.zip /app/dags/archive/'
    )

    archive_to_azure_blob = PythonOperator(
        task_id='archive_to_azure_blob',
        python_callable=blob_upload
    )

    delete_archive_files = BashOperator(
        task_id='delete_archive_files',
        bash_command='rm /app/dags/archive/*'
    )

    delete_stockx_files = BashOperator(
        task_id='delete_stockx_files',
        bash_command='rm /app/dags/stockx/*'
    )

    extract_data >> transform_load >> archive_json_files >> zip_to_archive >> archive_to_azure_blob >> [delete_archive_files, delete_stockx_files]