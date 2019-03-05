# Yandex Transport Monitor

*This project is for Russian "Yandex.Maps" and "Yandex.Transport" services, so it's expected that majority of potential users are from Russian federation, thus the README is written in Russian.*

Скрипт, позволяющий собирать данные Яндекс.Транспорта по конкретной остановке общественного транспорта, что делает возможным создание своего собственного табло прибытия для конкретной остановки, или автоматизировать какой-либо процесс в зависимости о данных о транспорте - например, будильник, вытаскивающий с мягкого и уютного дивана когда твой автобус подъезжает к дому или работе, а также собрать статистику по движению транспорта для дальнейшего анализа (следует ли он расписанию, когда прекращает ходить на самом деле).

![Yandex Transport Monitor Screenshot M](https://github.com/OwlSoul/YandexTransportMonitor/raw/master/images/sample-01.jpg)

## Какую проблему решает этот скрипт?

Это своеобразное "API" для "Яндекс.Транспорт", так как официального на данный момент не существует. Эта штука позволяет получить прогноз прибытия транспорта по одной конкретной остановке, выдать в формате CSV или обычным текстом в stdout, и, при желании, сохранить результат в базу данных (PostgreSQL).

Попытки получить данные Яндекс.Транспорта через curl в принципе возможны, но быстро приводят к "бану". Данные от "Транспорта" Яндекс в своих "Картах" передает при клике на остановку (выполняется AJAX-запрос, который возвращает JSON с данными транспорта, включая расчетное время прибытия на остановку), и данный JSON защищен с помощью CSRF-токена. С помощью curl можно получить его, сначала просто зайдя на Яндекс.Карты, получить и сохранить cookie, распарсить CSRF-токен, и уже с ним запросить JSON с данными о транспорте. Пару раз это работает, а потом Яндекс вежливо начинает просить ввести CAPTCHA. А вот если сидеть и методично кликать на остановку в браузере - к такому Яндекс, похоже, относится более чем адекватно.

Наглое решение проблемы - использовать браузер для сохранения и дальнейшего парсинга страницы. Лучше всего подходит Chromium, который переведен в headless (работа без GUI) режим, это позволяет запускать его на сервере (вся эта схема проверялась на двух ноутбуках, VPS в облаке, Raspberry PI и Orange PI). Для "дерганья за ниточки" браузера, как марионетку, существует отличная вещь WebDriver, и пакет Selenium для Python (который предназначен скорее для тестирования ПО, но можно и вот такие извращения делать).

Так как WebDriver достаточно серьезно завязан на версию Chromium, лучше всего запаковать все в Docker-контейнер (с определенной версией Chromium и совместимым WebDriver).

## Как этот скрипт работает?
Схема работы следующая:

1. Скрипт получает ссылку на остановку, по которой нужно получить данные.
2. Запускается Chromium в "headless" режиме, который проходит по этой ссылке, и исходный код страницы сохраняется.
3. Скрипт парсит данные из сохраненной страницы, и выводит их в stdout.
4. Опционально, если скрипт об этом "попросили", он сохранит результат и в базу данных (PostgreSQL).

Запускать скрипт чаще чем раз в минуту по одной остановке смысла нет, плюс он может работать в цикле, чтобы не открывать и не закрывать Chromium при каждом запросе данных с остановки - в конце концов Chromium штука тяжелая.

## Установка
### Вариант 1: Docker контейнер
Оптимальный вариант установки и использования скрипта - через Docker контейнер. Dockerfile для сборки находится в корневой директории проекта, для сборки образа контейнера достаточно выполнить следующую команду:

`sudo docker build -t "ytmonitor:latest" .`

По умолчанию часовой пояс установлен Московский (Europe/Moscow). Если требуется изменить часовой пояс на другой, это можно сделать либо поправив Dockerfile и заменив значение в данной строчке:

`ARG timezone="Europe/Moscow"`

на что-нибудь другое, например:

`ARG timezone="Asia/Vladivostok"`

Либо передав часовой пояс как параметр при сборке Docker контейнера:

`sudo docker build -t "ytmonitor:latest" --build-arg timezone="Asia/Vladivostok" .`

### Вариант 2: Классическая установка
Данный метод стоит использовать только если по какой-то причине невозможно использовать контейнеризацию, или  на диске занимаемое Docker образом слишком критично.

Инструкция приводится для Ubuntu, проверено на Ubuntu 18.04.

1. Подготовка к установке:

   `apt-get update`

2. Установка браузера (Chromium) и WebDriver. Здесь очень важно чтобы браузер и WebDriver были совместимы друг с другом.

   `apt-get install -y chromium-browser=71.0.3578.98-0ubuntu0.18.04.1` \
   `apt-get install -y chromium-chromedriver=71.0.3578.98-0ubuntu0.18.04.1`

3. Установка "Python 3" и "pip".

  `apt-get install python3 python3-pip`

4. Ряд дополнительных необходимых библиотек:

  `apt-get install libxml2-dev libpq-dev libxslt1-dev`

5. Установка необходимых пакетов для Python (pip):

   `pip3 install psycopg2-binary` \
   `pip3 install selenium` \
   `pip3 install setproctitle` \
   `pip3 install beautifulsoup4` \
   `pip3 install lxml==4.2.1`

6. Просто скопируйте скрипт куда угодно, например в домашнюю директорию.

   `cd ~/`
   `git clone https://github.com/OwlSoul/YandexTransportMonitor`

## Запуск скрипта
Chromium очень капризная штука, и как минимум будет отказываться просто так запускаться под root пользователем (хороший мальчик). При запуске же внутри Docker-контейнера он потребует себе дополнительных привилегий, потому что может.

В папке launch/docker размещен скрипт "monitor-example_maryino.sh" который легко отредактировать, и который запускает скрипт в контейнере (при условии что контейнер был до этого собран, конечно).

При условии что Docker-образ был собран, и назван "ytmonitor:latest", можно запустить скрипт из примеров:

`sudo ./monitor_maryino.sh`

Если текущий пользователь имеет право создавать Docker-контейнеры, sudo можно опустить.

Скрипт содержит в себе следующую команду:
```
#!/bin/bash

IMAGE="ytmonitor:latest"

docker run -it --privileged $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 1 \
--url "https://yandex.ru/maps/213/moscow/?ll=37.744365%2C55.649835&masstransit%5BstopId%5D=stop__9647488&mode=stop&sll=39.497656%2C43.958431$
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once
'
```

Запуск докер-контейнера в привелигированом режиме необходим для корректной работы Chromium, иначе он не может правильно работать с "user namespaces", которые ему так нужны. 

Скрипт проверит состояние остановки "Марьино" в г. Москва, и выдаст примерно следующую информацию:

```
Timestamp : 2019-03-04 09:48:40.676451
Station ID: stop__9647488
('1', '511', 'Автобус', '', '0', '', '')
('2', '623', 'Автобус', '', '8', '14', '')
('3', '415', 'Автобус', '', '10', '', '')
('4', '965', 'Автобус', '', '12', '26', '')
('5', '280', 'Автобус', '', '13', '42', '11:02')
('6', '541', 'Автобус', '', '14', '', '')
('7', '517', 'Автобус', '', '15', '', '')
('8', 'Южные Ворота - Марьино', 'Маршрутка', '12', '', '', '')
('9', '897', 'Маршрутка', '15', '', '', '')
('10', 'Ашан - Братиславская', 'Автобус', '25', '', '', '')
('11', 'Южные Ворота - Братиславская', 'Маршрутка', '30', '', '', '')
('12', 'н5', 'Автобус', '', '', '', '')
```

Timestamp: время в которое был сделан запрос.

Station_ID: ID станции. Данное поле в принципе может быть любым, например "ID_OKRUZHNAYA", скрипт не руководствуется им при запросе, ID передается как параметр чтобы было что показать в выводе и/или записать в базу данных. Однако, если ID не был передан скрипту, он попробует автоматически определить его из URL.

Далее, каждая строка представляет из себя информацию о конкретном транспорте, в следующем формате:

`('Порядковый номер', 'номер маршрута', 'тип транспорта', 'частота рейсов', 'время до ближайшего прибытия', 'время до следующих прибытий', 'точное время отправления')`

Номер маршрута, как видно из примера, может быть как и простым (511, н5), так и длинной, сложной b и абсолютно недружелюбной к инфо-табло строкой ("Южные Ворота - Братиславская"), обычно для маршруток.
Для рейсов, у которых есть расчетное время прибытия на остановку, частота обычно не указывается, и наоборот, если указана частота рейсов, скорее всего прогноза прибытия не будет (на маршруте не установлена спутниковая система слежения).

Расчетное время прибытия специально разделено на "ближайшее" и "последующие", в ближайшем будет всегда всего одно число, тогда как в последующих может быть несколько чисел разделенных пробелом, если, например, к остановке уже подъезжает несколько автобусов одного маршрута.

Наконец, для некоторых автобусов, не часто выполняющих свои рейсы, иногда будет доступна информация о "точном отправлении", особенно если станция конечная (как автобус 280 в примере).

Автобус н5 в данном примере - ночной, а запрос сделан рано утром, поэтому никаких данных по автобусу просто нет (это значит ждать его в момент запроса точно бесполезно).

Все время (интервал, прибытие) указано в минутах.

Другой пример, остановка "Бауманская" (`sudo monitor_baumanskaya.sh`):

```
Timestamp : 2019-03-04 09:59:17.417794
Station ID: Бауманская
('1', '50', 'Трамвай', '', '2', '7 14', '')
('2', '37', 'Трамвай', '', '4', '18', '')
('3', '45', 'Трамвай', '', '12', '13 23', '')
('4', 'Б', 'Трамвай', '', '13', '26', '')
('5', '425', 'Автобус', '', '20', '', '')
```

Здесь хорошо видно несколько прибытий трамвая 50 и 45 к данной остановке. Например читать строку `('3', '45', 'Трамвай', '', '12', '13 23', '')` следует следующим образом:
Трамвай 45 приедет через 12 минут, следующий 45й приедет через 13 минут после первого, а потом еще один, через 23 минуты после первого (то есть через 10 минут после 2-го).

Формат вывода в предыдущих двух примерах можно поменять на csv (см пример "monitor_baumanskaya_csv.sh"):
```
1,2019-03-04 13:14:42.916162,stop__9643291,50,Трамвай,,0,6 24,
2,2019-03-04 13:14:42.916162,stop__9643291,37,Трамвай,,4,25 26,
3,2019-03-04 13:14:42.916162,stop__9643291,45,Трамвай,,5,8 30,
4,2019-03-04 13:14:42.916162,stop__9643291,425,Автобус,,5,,
5,2019-03-04 13:14:42.916162,stop__9643291,Б,Трамвай,,12,26,
```

Здесь структура данных следующая:

`Порядковый номер, временной штамп, номер маршрута, тип транспорта, частота рейсов, время до ближайшего прибытия, время до следующих прибытий, точное время отправления`

Важно отметить, что скрипт внутри контейнера запускается не от имени root пользователя, а от имени пользователя ytmonitor.

Примеры для запуска скрипта если он был установлен не из контейнера можно посмотреть просто в папке "launch". Основной скрипт в данном случае - "ytm_wd".

## Параметры командной строки
Скрпт принимает следующие параметры командной строки:

----

`--verbose VERBOSE_LEVEL` - "болтливость" скрипта, может принимать значения от 0 до 4, например `--verbose 3`. \
0 - только результат stdout, даже если произошла фатальная ошибка. \
1 - вывод сообщений об ошибках (ERROR) \
2 - вывод сообщений об ошибках и предупреждений (WARNING) \
3 - вывод сообщений об ошибках, предупреждений и информационных сообщений (INFO) \
4 - полная отладка, выводит все что только можно (DEBUG)

----

`--url URL` основной и самый важный параметр. URL остановки. Выглядит обычно так себе:

`--url https://yandex.ru/maps/213/moscow/?ll=37.744365%2C55.649835&masstransit%5BstopId%5D=stop__9647488&mode=stop&sll=39.497656%2C43.958431&sspn=0.291481%2C0.128713&text=%D0%BC%D0%B0%D1%80%D1%8C%D0%B8%D0%BD%D0%BE%20%D0%BC%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&z=17`

![Yandex Transport Monitor Screenshot 2](https://github.com/OwlSoul/YandexTransportMonitor/raw/master/images/sample-02.jpg)

Чтобы получить этот url, нужно зайти в Яндекс.Карты, найти интересующую остановку, нажать на нее (должен открыться прогноз прибытия транспорта), и скопировать весь URL. Координаты (ll=...) лучше не упускать, все-таки мы "притворяемся человеком" чтобы избежать CAPTCHA. Яндексу не стоит знать что роботы уже здесь, и он им не нравится.

----

`--chrome-driver-location LOCATION`, путь до WebDriver, если последний находится в PATH то Selenium его и так найдет, но из репозитория оно ставится вот сюда:

`--
chrome_driver_location "/usr/lib/chromium-browser/chromedriver"`

----
`--run_once`, запустить скрипт только один раз, получить данные и выйти.

----
`--wait_time WAIT_TIME`, время между запросами. По умолчанию 60 секунд.

Пример `wait_time 50`. Если параметр `--run_once` не был указан, данный параметра (`wait_time`) вступает в силу, и скрипт будет опрашивать остановку пока не будет остановлен (сигналами SIGINT, SIGTERM или SIGKILL), ожидая указанное время в секундах между запросами.

Важно, что это именно время ОЖИДАНИЯ, а не время между запросами, при указании "60" скрипт будет опрашивать остановку не каждые 60 секунд, а чуть реже (время опроса + 60 секунд).

----
`--out_mode MODE`, режим вывода. "plain" или "csv". По умолчанию - "plain".

----
--`save_to_database`, если параметр присутствует, то скрипт попытается сохранить их в базу данных.

Параметры базы данных PostgreSQL (если запись в базу включена):

`--db_host "localhost" ` - хост \
`--db_port 5432 ` - порт \
`--db_name "ytmonitor" ` - база данных \
`--db_username "ytmonitor" ` - пользователь \
`--db_password "password" ` - пароль \

----
## Создание базы данных
Следующие команды для PostgreSQL создадут необходимую базу данных, с которой скрипт может работать:

```
CREATE ROLE ytmonitor WITH LOGIN ENCRYPTED PASSWORD 'password';

CREATE DATABASE ytmonitor WITH OWNER ytmonitor;

\c ytmonitor;

CREATE TABLE transit(
seq_id serial primary key,
stop_id varchar,
stamp timestamptz,
route varchar,
type varchar,
frequency varchar,
prognosis varchar,
prognosis_more varchar,
departures varchar
);

GRANT ALL PRIVILEGES ON DATABASE ytmonitor TO ytmonitor;

GRANT ALL PRIVILEGES ON TABLE transit TO ytmonitor;

GRANT USAGE, SELECT ON SEQUENCE transit_seq_id_seq TO ytmonitor;
```

## Поддержка и обратная связь.
Яндекс может в любой момент поменять дизайн своих карт или той части что отвечает за Транспорт. Поскольку данный скрипт это парсер, скорее всего в таком случае работать он перестанет. Один раз это уже произошло, в процессе разработки (отсюда 1.1.Х в версии, а не 1.0.Х). Если это произойдет еще раз - автоматическая система
оповестит автора об этом в течении 2-х часов, и можно ждать оперативный фикс, если он будет возможен.

Как только (и если) Яндекс выпустит API для Транспорта, поддержка данного "чудовища" будет скорее всего прекращена.

В любом случае, сообщить о возникшей проблеме всегда можно здесь:
https://github.com/OwlSoul/YandexTransportMonitor/issues/new

## Лицензия
Исходный код распространяется под лицензией MIT.

Исходный код предоставляется "Как есть (As Is)", автор ответственности за возможные проблемы при его использовании не несет.
