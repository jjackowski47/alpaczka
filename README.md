To run all docker containers use docker-compose.yml file, type:

```
docker-compose up
```

In order to initialize database with couriers and parcel lockers entities go to endpoint

[https://localhost:7000/initRedis](https://localhost:7000/initRedis)

Automaticly generated couriers accounts credentials:
|No.| login | password |
|:-:|:--------:| :-------: |
| 1 | courier1 | Courier1# |
| 2 | courier2 | Courier2# |
| 3 | courier3 | Courier3# |
| 4 | courier4 | Courier4# |
| 5 | courier5 | Courier5# |

Przykładowe identyfikatory paczkomatów zostaną wygenerowane losowo i zostaną zapisane do zbioru w bazie redis.

Project consists of 4 applications running on ports:
| Port | Description |
|:----:|:--------------------------------------------------------------------------------------|
|:7000 |client app (ragistration, login, genereting and viewing waybills) |
|:7001 |stateless file manager app (download, remove) |
|:7002 |progressive courier app |
|:7003 |parcel locker app |

There is an option to log in to courier or client app via OAuth method.

To start PWA features u have to run your browswer in insecure mode for example for Chrome on Windows cmd:

```
start chrome --ignore-certificate-errors --unsafely-treat-insecure-origin-as-secure=https://localhost:7002 --allow-insecure-localhost https://localhost:7002
```
