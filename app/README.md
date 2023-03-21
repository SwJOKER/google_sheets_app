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
docker-compose up -d --build
```
## Warning
On first start celery-beat service can start working before migrations.
In that case you need restart celery-beat service, when all migrates will be done
```
docker-compose restart celery-beat
```

## Sheets registration
For register new sheet you can just put google sheet's key in URL.
```
# like 
http://localhost:8000/sheet/1MuMERz8I1Qd8Ip4DB8UrbPD4fgdSbmE-YVMPistsqkE/

# In this case key:
1MuMERz8I1Qd8Ip4DB8UrbPD4fgdSbmE-YVMPistsqkE
```
Key will checked for length. If not permissions to access it will not be created. 
If all ok you can reload page little bit later and see your doc.

## Telegram
For subscribe for notifications you need send start command in chat with bot.
```
/start
```
It will ask secret word. By default:
```
foo
```
Could be modified in .env.dev

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