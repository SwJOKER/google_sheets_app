# Google Sheet Microservice

Service for parsing google sheets to database and providing summary info to webpage.
Service check orders in file for date expiring and send notifies to subscribers in telegram. 

# Quick start

There is docker container. Before start container you need put Google API key to 'app' 
directory with name:
```
'service-key.json'
```
You can customize it in 
```
.env.dev

SHEETS_JSON_KEY=service-key.json
```
Additionaly in .env.dev you must define next variables:
```
# code for authorize in telegram for subscribe for updates.
# can be any as you wish
TELEGRAM_CLIENT_CODE=foo

# Token from Telegram BotFather
TELEGRAM_BOT_TOKEN=xxx
```
After that you can run docker-container from project directory
```
docker-composeв up -d --build
```

## Warnings
On first start celery-beat service can start working before migrations.
In that case you need restart celery-beat service, when all migrates will be done
```
docker-compose restart celery-beat
```

## Sheets registration
For register new sheet you can just put google sheet's key in URL.
Document example:
```
https://docs.google.com/spreadsheets/d/13nUkBwlXYGmDmYUkkhAgkA_v8mxeh9H9ePp5NkKiDXY

# like 
http://localhost:8000/sheets/13nUkBwlXYGmDmYUkkhAgkA_v8mxeh9H9ePp5NkKiDXY/

# In this case key is:
13nUkBwlXYGmDmYUkkhAgkA_v8mxeh9H9ePp5NkKiDXY

```
Key will checked for length. If not permissions to access it will not be created. 
If all ok you can reload page little bit later and see your doc.

Sheets list address:
```
http://localhost:8000/sheets/
```
## Telegram
For subscribe for notifications you need send start command in chat with bot.
```
/start
```
For unsubscribe:
```
/stop
```
It will ask secret word. By default:
```
TELEGRAM_CLIENT_CODE=foo
```
Could be modified in .env.dev

By default delivery date checking scheduled on 7 AM. In DEBUG mode it repeats every 30 seconds.
Notificate sends once for each expired delivery order.

## Api 
There is API for react app which i did not have time to do.
Its simple REST app. 
You can get information about registered sheets by address
```
http://localhost:8000/api/sheets
```
Retrieve certain sheet:
```
http://localhost:8000/api/sheets/<key>
```
For full information about sheet with orders you need add variable full=1 to URL:
```
http://localhost:8000/api/sheets/<key>/?full=1

http://localhost:8000/api/sheets/?full=1
```

## Start production
Start container from docker-compose.prod.yml
```
docker-compose -f docker-compose.prod.yml up -d --build
```
After start needed do migrations and collect static files
```
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py makemigrations sheets_to_web
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic
```
After this restart celery-beat worker
```
docker-compose restart celery-beat
```
