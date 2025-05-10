- [What is this package?](#what-is-this-package)
- [Quick start](#quick-start)
- [HOWTO](#howto)
  * [Install](#install)
  * [Database](#database)
  * [Read](#read-operations)
  * [Create](#create-operations)
  * [Delete](#delete-operations)
  * [Update](#update-operations)
- [Conceptual approach](docs/conceptual-approach.md)
- [Keyset pagination](docs/keyset-pagination.md)

# What is this package?

A Python API on top of the FreeRADIUS database for automation purposes.

* It provides an [object-oriented view](docs/conceptual-approach.md#class-diagram) of the database schema
* It implements [some logic](docs/conceptual-approach.md#domain-logic) to ensure data consistency

> Originally embedded in [freeradius-api](https://github.com/angely-dev/freeradius-api), it is now a separate and ready-to-use package.

Other than Pydantic, it only relies on Python builtins.

## What database support?

It works with MySQL, MariaDB, PostgreSQL and SQLite using DB-API 2.0 ([PEP 249](https://peps.python.org/pep-0249/)) compliant drivers such as:

```
mysql-connector-python
psycopg
psycopg2
pymysql
pysqlite3
sqlite3
```

It may work with other compliant drivers, yet not tested.

## Repository and Service layers

This package comes with two usable layers named as per the [DDD (Domain-Driven Design)](docs/conceptual-approach.md):

* **Repository layer**—responsible for mapping the (domain) objects to the database
* **Service layer**—responsible for maintaining the (domain) logic using the repositories

In other words, **the service layer guarantees you data consistency and is the recommended one.**

> Yet you are free to use the repository layer and implement your own logic over it.

The [HOWTO](#howto) focuses on services.

<img src="https://user-images.githubusercontent.com/4362224/202743771-07877b22-da82-4967-8bd5-1e62bb2f1e9a.png" width="600" />

# Quick start

Install `pyfreeradius` and the appropriate DB-API 2.0 driver:

```sh
python3 -m venv venv
source venv/bin/activate
#
pip install pyfreeradius
pip install mysql-connector-python
```

## Database

An instance of the FreeRADIUS server is NOT needed for testing, the focus being on the database schema.

Either you use an existing database or (preferably) a Docker container for testing the package:

```sh
wget https://github.com/angely-dev/pyfreeradius/archive/refs/heads/main.zip
unzip main.zip
cd pyfreeradius-main/tests/docker
#
docker compose -f docker-compose-mysql.yml up -d --wait
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' docker-mydb-1
# 172.18.0.2
sudo echo "172.18.0.2 mydb" | sudo tee -a /etc/hosts
ping mydb
# PING mydb (172.18.0.2) 56(84) bytes of data.
# 64 bytes from mydb (172.18.0.2): icmp_seq=1 ttl=64 time=0.234 ms
```

## Example #1

Find all groupnames, usernames and NAS names (number of results is limited to `100` by default):

```py
from mysql.connector import connect
from pyfreeradius import Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

print(services.user.find_usernames())
print(services.group.find_groupnames())
print(services.nas.find_nasnames())

db_session.close()
```

## Example #2

Create a group, a user in the group and a NAS:

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import AttributeOpValue, Group, Nas, User, UserGroup

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

# Create a group
group = Group(
    groupname="my-group",
    replies=[
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
        AttributeOpValue(attribute="Framed-IP-Netmask", op=":=", value="255.255.255.255"),
    ],
)
services.group.create(group)

# Create a user while adding it to the group
user = User(
    username="my-user",
    groups=[UserGroup(groupname="my-group")],
    checks=[AttributeOpValue(attribute="Cleartext-Password", op=":=", value="password")],
    replies=[
        AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.78"),
        AttributeOpValue(attribute="Framed-Route", op="+=", value="192.168.1.0/24"),
        AttributeOpValue(attribute="Framed-Route", op="+=", value="192.168.2.0/24"),
        AttributeOpValue(attribute="Framed-Route", op="+=", value="192.168.3.0/24"),
    ],
)
services.user.create(user)

# Create a NAS
nas = Nas(nasname="192.168.1.1", shortname="my-shortname", secret="my-secret")
services.nas.create(nas)

db_session.commit()
db_session.close()
```

## Example #3

Use `pyfreeradius` to build a REST API: you may be interested in [freeradius-api](https://github.com/angely-dev/freeradius-api) project.

# HOWTO

## Install

`pyfreeradius` is available on [PyPI](https://pypi.org/project/pyfreeradius):

```
pip install pyfreeradius
```

## Database

### Session

The app which makes use of `pyfreeradius` is responsible for establishing and closing the database connection as well as handling the transaction lifecycle:

```py
from mysql.connector import connect
from pyfreeradius import Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

# some service calls
# …

db_session.commit()
db_session.close()
```

The example above imports `connect` from `mysql-connector-python` driver. Depending on your SQL backend, you have to import it from the appropriate DB-API 2.0 driver, e.g.:

```py
from pymysql import connect
db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
```
```py
from psycopg import connect
db_session = connect("user=raduser password=radpass host=mydb dbname=raddb")
```
```py
from sqlite3 import connect
db_session = connect("my-database.db")
```

### Table names (optional)

By default, the following table names are used:

```py
from pyfreeradius import RadTables

RadTables()
# RadTables(
#     radcheck='radcheck',
#     radreply='radreply',
#     radgroupcheck='radgroupcheck',
#     radgroupreply='radgroupreply',
#     radusergroup='radusergroup',
#     nas='nas',
# )
```

To change all or part of the table names:

```py
from mysql.connector import connect
from pyfreeradius import RadTables, Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
rad_tables = RadTables(
    radcheck="my-radcheck-table",
    radreply="my-radreply-table",
)
services = Services(db_session=db_session, rad_tables=rad_tables)

# some service calls
# …

db_session.commit()
db_session.close()
```

## Read operations

As an overview:

* `find` returns all items (number of results is limited to `100` by default, [see filtering and limiting](#filtering-and-pagination-with-find))
* `find_one` returns one item if it exists, `None` otherwise
* `get` returns the item if it exists, raises a `NotFound` error otherwise
* `exists` returns `True` if the item exists, `False` otherwise

Just like `find`, there are also `find_*names` methods. They could be handy for a quick retrieval test.

### Get users

```py
services.user.find_usernames()
# ['alice@adsl', 'bob', 'eve', 'oscar@adsl']

services.user.find()
# [User(username='alice@adsl', …), User(username='bob', …), User(username='eve', …), User(username='oscar@adsl', …)]
services.user.find(limit=2)
# [User(username='alice@adsl', …), User(username='bob', …)]

services.user.find(username_like="%adsl")
# [User(username='alice@adsl', …), User(username='oscar@adsl', …)]

services.user.exists("alice@adsl")
# True
services.user.exists("mallory")
# False

services.user.find_one("alice@adsl")
services.user.get("alice@adsl")
# User(
#     username='alice@adsl',
#     checks=[AttributeOpValue(attribute='Cleartext-Password', op=':=', value='alice-pass')],
#     replies=[
#         AttributeOpValue(attribute='Framed-IP-Address', op=':=', value='10.0.0.2'),
#         AttributeOpValue(attribute='Framed-Route', op='+=', value='192.168.1.0/24'),
#         AttributeOpValue(attribute='Framed-Route', op='+=', value='192.168.2.0/24'),
#         AttributeOpValue(attribute='Huawei-Vpn-Instance', op=':=', value='alice-vrf'),
#     ],
#     groups=[UserGroup(groupname='100m', priority=1)],
# )

services.user.find_one("mallory")
# None
services.user.get("mallory")
# pyfreeradius.services.ServiceExceptions.UserNotFound: Given user does not exist
```

### Get groups

```py
services.group.find_groupnames()
# ['100m', '200m', '250m']

services.group.find()
# [Group(groupname='100m', …), Group(groupname='200m', …), Group(groupname='250m', …)]
services.group.find(limit=2)
# [Group(groupname='100m', …), Group(groupname='200m', …)]

services.group.find(groupname_like="2%")
# [Group(groupname='200m', …), Group(groupname='250m', …)]

services.group.exists("100m")
# True
services.group.exists("300m")
# False

services.group.find_one("100m")
services.group.get("100m")
# Group(
#     groupname='100m',
#     checks=[],
#     replies=[AttributeOpValue(attribute='Filter-Id', op=':=', value='100m')],
#     users=[
#         GroupUser(username='bob', priority=1),
#         GroupUser(username='alice@adsl', priority=1),
#         GroupUser(username='eve', priority=1),
#     ],
# )

services.group.find_one("300m")
# None
services.group.get("300m")
# pyfreeradius.services.ServiceExceptions.GroupNotFound: Given group does not exist
```

### Get NASes

```py
services.nas.find_nasnames()
# ['3.3.3.3', '4.4.4.4', '4.4.4.5']

services.nas.find()
# [Nas(nasname='3.3.3.3', …), Nas(nasname='4.4.4.4', …), Nas(nasname='4.4.4.5', …)]
services.nas.find(limit=2)
# [Nas(nasname='3.3.3.3', …), Nas(nasname='4.4.4.4', …)]

services.nas.find(nasname_like="4.4.4.%")
# [Nas(nasname='4.4.4.4', …), Nas(nasname='4.4.4.5', …)]

services.nas.exists('3.3.3.3')
# True
services.nas.exists('5.5.5.5')
# False

services.nas.find_one('3.3.3.3')
services.nas.get('3.3.3.3')
# Nas(
#     nasname='3.3.3.3',
#     shortname='my-super-nas',
#     secret='my-super-secret'
# )

services.nas.find_one('5.5.5.5')
# None
services.nas.get('5.5.5.5')
# pyfreeradius.services.ServiceExceptions.NasNotFound: Given NAS does not exist
```

### `find_one` vs `get`

The former returns `None` if the item is not found whereas the latter raises a `NotFound` error.

### Filtering and pagination with `find`

`find` returns a list of items ordered by name, i.e., by `username`, `groupname` or `nasname`:

```py
services.user.find()
services.group.find()
services.nas.find()
```

Filtering results is possible through the `*name_like` parameter:

```py
services.user.find(username_like="%@realm")
services.group.find(groupname_like="VPN-%")
services.nas.find(nasname_like="192.168.%")

# the same applies for *names methods
services.user.find_usernames(username_like="%@realm")
services.group.find_groupnames(groupname_like="VPN-%")
services.nas.find_nasnames(nasname_like="192.168.%")
```

As a precaution, `find` returns a limited number of results (`100` by default). To get more or even all results, either:

* Increase the limit:
```py
services.user.find(limit=900)
services.group.find(limit=900)
services.nas.find(limit=900)

# the same applies for *names methods
services.user.find_usernames(limit=900)
services.group.find_groupnames(limit=900)
services.nas.find_nasnames(limit=900)
```
* Disable the limit:
```py
# all items will be returned, be cautious!
services.user.find(limit=None)
services.group.find(limit=None)
services.nas.find(limit=None)

# the same applies for *names methods
services.user.find_usernames(limit=None)
services.group.find_groupnames(limit=None)
services.nas.find_nasnames(limit=None)
```
* Use [keyset pagination](docs/keyset-pagination.md) via the `*name_gt` parameter (_gt_ stands for _greater than_):
```py
# iterate through all users
# the same applies for groups ans NASes
# as well as *names methods

all_users = []
users = services.user.find()
while users:
    all_users += users
    last_user = users[-1]
    users = services.user.find(username_gt=last_user.username)
print(len(all_users))
```

> Pagination may be useful for a frontend app which lists users through infinite scrolling.

All the above parameters can combine, e.g.:

```py
services.user.find(username_like="%@realm", username_gt="cust123", limit=5)
services.user.find_usernames(username_like="%@realm", username_gt="cust123", limit=5)
```

## Create operations

### Create a user

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import AttributeOpValue, User

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

user = User(
    username="my-user",
    checks=[AttributeOpValue(attribute="Cleartext-Password", op=":=", value="password")],
    replies=[
        AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.1"),
        AttributeOpValue(attribute="Framed-IP-Netmask", op=":=", value="255.255.255.255"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
    ],
)

services.user.exists("my-user")
# False
services.user.create(user)
services.user.exists("my-user")
# True
services.user.create(user)
# pyfreeradius.services.ServiceExceptions.UserAlreadyExists: Given user already exists

db_session.commit()
db_session.close()
```

### Create a user within groups

> This allows to create a user while adding it to groups. To modify an existing user, see [update operation](#update-a-user).

```py
from pyfreeradius.models import UserGroup

user = User(
    username="my-user",
    checks=[AttributeOpValue(attribute="Cleartext-Password", op=":=", value="password")],
    replies=[
        AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.1"),
        AttributeOpValue(attribute="Framed-IP-Netmask", op=":=", value="255.255.255.255"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
    ],
    groups=[
        UserGroup(groupname="my-group-1"),  # priority defaults to 1
        UserGroup(groupname="my-group-2", priority=2),
    ],
)

services.group.get("my-group-1").contains_user("my-user")
# False
services.user.create(user)
services.group.get("my-group-1").contains_user("my-user")
# True
```

If one of the group does not exist, a `GroupNotFound` error will be raised:

```py
services.user.create(user)
# pyfreeradius.services.ServiceExceptions.GroupNotFound:
#  Given group 'my-group-2' does not exist:
#  create it first or set 'allow_groups_creation' parameter to true
```

Ideally, groups must be created first. Alternatively, the `allow_groups_creation` option can be enabled:

```py
services.group.exists("my-group-2")
# False
services.user.create(user, allow_groups_creation=True)
services.group.exists("my-group-2")
# True
```

This results in creating the missing groups (without any attributes):

```py
services.group.get("my-group-2")
# Group(groupname='my-group-2', checks=[], replies=[], users=[GroupUser(username='my-user', priority=2)])
```

The newly created groups can be updated later to set their attributes.

### Create a group

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import AttributeOpValue, Group

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

group = Group(
    groupname="my-group",
    replies=[
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
    ],
)

services.group.exists("my-group")
# False
services.group.create(group)
services.group.exists("my-group")
# True
services.group.create(group)
# pyfreeradius.services.ServiceExceptions.GroupAlreadyExists: Given group already exists

db_session.commit()
db_session.close()
```

### Create a group with users

> This allows to create a group while adding users in it. To modify an existing group, see [update operation](#update-a-group).

```py
from pyfreeradius.models import GroupUser

group = Group(
    groupname="my-group",
    replies=[
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
    ],
    users=[
        GroupUser(username="my-user-1"),  # priority defaults to 1
        GroupUser(username="my-user-2", priority=2),
    ],
)

services.user.get("my-user-1").belongs_to_group("my-group")
# False
services.group.create(group)
services.user.get("my-user-1").belongs_to_group("my-group")
# True
```

If one of the user does not exist, a `UserNotFound` error will be raised:

```py
services.group.create(group)
# pyfreeradius.services.ServiceExceptions.UserNotFound:
#  Given user 'my-user-2' does not exist:
#  create it first or set 'allow_users_creation' parameter to true
```

Ideally, users must be created first. Alternatively, the `allow_users_creation` option can be enabled:

```py
services.user.exists("my-user-2")
# False
services.group.create(group, allow_users_creation=True)
services.user.exists("my-user-2")
# True
```

This results in creating the missing users (without any attributes):

```py
services.user.get("my-user-2")
# User(username='my-user-2', checks=[], replies=[], groups=[UserGroup(groupname='my-group', priority=2)])
```

The newly created users can be updated later to set their attributes.

### Create a NAS

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import Nas

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

nas = Nas(nasname="192.168.1.1", shortname="my-shortname", secret="my-secret")

services.nas.exists("192.168.1.1")
# False
services.nas.create(nas)
services.nas.exists("192.168.1.1")
# True
services.nas.create(nas)
# pyfreeradius.services.ServiceExceptions.NasAlreadyExists: Given NAS already exists

db_session.commit()
db_session.close()
```

## Delete operations

### Delete a user

The `delete` operation deletes all user attributes and group belongings:

```py
from mysql.connector import connect
from pyfreeradius import Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

services.user.exists("my-user")
# True
services.user.delete("my-user")
services.user.exists("my-user")
# False
services.user.delete("my-user")
# pyfreeradius.services.ServiceExceptions.UserNotFound: Given user does not exist

db_session.commit()
db_session.close()
```

If the user belongs to a group without any attributes and no other users, this group would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore). The `delete` operation prevents this by default:

```py
services.user.get("my-user").groups
# [UserGroup(groupname='my-group', priority=1)]

services.group.find_one("my-group")
# Group(groupname='my-group', checks=[], replies=[], users=[GroupUser(username='my-user', priority=1)])

services.user.delete("my-user")
# pyfreeradius.services.ServiceExceptions.GroupWouldBeDeleted:
#  Group 'my-group' would be deleted as it has no attributes and no other users:
#  delete it first or set 'prevent_groups_deletion' parameter to false

services.user.delete("my-user", prevent_groups_deletion=False)

services.group.find_one("my-group")
# None
```

### Delete a group

The `delete` operation deletes all group attributes and user belongings to the group:

```py
from mysql.connector import connect
from pyfreeradius import Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

services.group.exists("my-group")
# True
services.group.delete("my-group")
services.group.exists("my-group")
# False
services.group.delete("my-group")
# pyfreeradius.services.ServiceExceptions.GroupNotFound: Given group does not exist

db_session.commit()
db_session.close()
```

A `GroupStillHasUsers` error is raised though if the group still has users:

```py
services.group.get("my-group").users
# [GroupUser(username='my-user-1', priority=1), GroupUser(username='my-user-2', priority=2)]

services.group.delete("my-group")
# pyfreeradius.services.ServiceExceptions.GroupStillHasUsers:
#  Given group still has users:
#  delete them first or set 'ignore_users' parameter to true

services.user.get("my-user-1").belongs_to_group("my-group")
# True
services.group.delete("my-group", ignore_users=True)
services.user.get("my-user-1").belongs_to_group("my-group")
# False
```

If the group contains a user without any attributes and no other groups, this user would disappear as per the FreeRADIUS schema (i.e., it wouldn't exist in the database anymore). The `delete` operation prevents this by default:

```py
services.group.get("my-group").users
# [GroupUser(username='my-user', priority=1)]

services.user.find_one("my-user")
User(username='my-user', checks=[], replies=[], groups=[UserGroup(groupname='my-group', priority=1)])

services.group.delete("my-group")
# pyfreeradius.services.ServiceExceptions.GroupStillHasUsers:
#  Given group still has users:
#  delete them first or set 'ignore_users' parameter to true

services.group.delete("my-group", ignore_users=True)
# pyfreeradius.services.ServiceExceptions.UserWouldBeDeleted:
#  User 'my-user' would be deleted as it has no attributes and no other groups:
#  delete it first or set 'prevent_users_deletion' parameter to false

services.group.delete("my-group", ignore_users=True, prevent_users_deletion=False)

services.user.find_one("my-user")
# None
```

### Delete a NAS

```py
from mysql.connector import connect
from pyfreeradius import Services

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")

services = Services(db_session)

services.nas.exists("192.168.1.1")
# True
services.nas.delete("192.168.1.1")
services.nas.exists("192.168.1.1")
# False
services.nas.delete("192.168.1.1")
# pyfreeradius.services.ServiceExceptions.NasNotFound: Given NAS does not exist

db_session.commit()
db_session.close()
```

## Update operations

### TL;DR

It is generally simpler to just delete and recreate the item.

> However, there are situations when updating is preferable, e.g., deleting a group to change its attributes would delete all user belongings which will have to be recreated. Therefore, updating just the group attributes seems more appropriate.

### Update strategy (JSON Merge Patch)

Updates are made possible using three complex parameters (which are Pydantic models):

```py
from pyfreeradius.params import UserUpdate
from pyfreeradius.params import GroupUpdate
from pyfreeradius.params import NasUpdate
```

They allow to change all or part of the field values, except for the `*name`.

> That is, in order to change the `username` of a user, it is required to delete it and recreate it.

The update strategy follows [RFC 7396](https://datatracker.ietf.org/doc/html/rfc7396) (JSON Merge Patch) guidelines:

* omitted fields during the update are not modified
* `None` value means removal (i.e., resets a field to its default value)
* **a list field can only be overwritten (replaced)**

As a consequence of the last point, to add attributes to an existing user, you must fetch the existing attributes first, combine them with the new ones, and send the result as the update parameter.

### Update a user

Below we add (overwrite) reply attributes of an existing user and remove all of its group belongings.

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import AttributeOpValue
from pyfreeradius.params import UserUpdate

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

services.user.get("my-user")
# User(
#     username="my-user",
#     checks=[AttributeOpValue(attribute="Cleartext-Password", op=":=", value="password")],
#     replies=[AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.1")],
#     groups=[UserGroup(groupname="my-group", priority=1)],
# )

fields_to_update = UserUpdate(
    replies=[
        AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.1"),
        AttributeOpValue(attribute="Framed-IP-Netmask", op=":=", value="255.255.255.255"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
        AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
    ],
    groups=None,  # or groups=[]
)

services.user.update("my-user", user_update=fields_to_update)
services.user.get("my-user")
# User(
#     username="my-user",
#     checks=[AttributeOpValue(attribute="Cleartext-Password", op=":=", value="password")],
#     replies=[
#         AttributeOpValue(attribute="Framed-IP-Address", op=":=", value="10.0.0.1"),
#         AttributeOpValue(attribute="Framed-IP-Netmask", op=":=", value="255.255.255.255"),
#         AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF"),
#         AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:ip-unnumbered=Loopback10"),
#     ],
#     groups=[],
# )

db_session.commit()
db_session.close()
```

The `update` operation logic is not trivial and is a mix of `create` and `delete` operations. Therefore, if a list of `groups` is given as an update parameter, it may raise:

* `GroupNotFound` error—if one of the given groups does not exist (unless `allow_groups_creation` is enabled)
* `GroupWouldBeDeleted` error—if one of the current user groups would result in a deletion (unless `prevent_groups_deletion` is disabled)

> A group would result in a deletion if it has no attributes and no other users than the one updated.

In addition, it ensures the new fields won't result in user deletion as per the FreeRADIUS schema (that is, a user without any attributes and no groups). A `UserWouldBeDeleted` error may be raised in that sense.

### Update a group

Below we remove check attributes of an existing group and add (overwrite) user belongings.

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.models import GroupUser
from pyfreeradius.params import GroupUpdate

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

services.group.get("my-group")
# Group(
#     groupname="my-group",
#     checks=[AttributeOpValue(attribute="Auth-Type", op=":=", value="Accept")],
#     replies=[AttributeOpValue(attribute="Cisco-AVPair", op="+=", value="ip:vrf-id=MY-VRF")],
#     users=[GroupUser(username="my-user-1", priority=1)],
# )

fields_to_update = GroupUpdate(
    checks=[],  # or checks=None
    users=[GroupUser(username="my-user-1"), GroupUser(username="my-user-2")],
)

services.group.update("my-group", group_update=fields_to_update)
services.group.get("my-group")
# Group(
#     groupname="my-group",
#     checks=[],
#     replies=[AttributeOpValue(attribute="Cisco-AVPair", op=":=", value="ip:vrf-id=MY-VRF")],
#     users=[GroupUser(username="my-user-1", priority=1), GroupUser(username="my-user-2", priority=1)],
# )

db_session.commit()
db_session.close()
```

The `update` operation logic is not trivial and is a mix of `create` and `delete` operations. Therefore, if a list of `users` is given as an update parameter, it may raise:

* `UserNotFound` error—if one of the given users does not exist (unless `allow_users_creation` is enabled)
* `UserWouldBeDeleted` error—if one of the current group users would result in a deletion (unless `prevent_users_deletion` is disabled)

> A user would result in a deletion if it has no attributes and no other groups than the one updated.

In addition, it ensures the new fields won't result in group deletion as per the FreeRADIUS schema (that is, a group without any attributes and no users). A `GroupWouldBeDeleted` error may be raised in that sense.

### Update a NAS

Below we only update the secret of an existing NAS:

```py
from mysql.connector import connect
from pyfreeradius import Services
from pyfreeradius.params import NasUpdate

db_session = connect(user="raduser", password="radpass", host="mydb", database="raddb")
services = Services(db_session)

services.nas.get("192.168.1.1")
# Nas(nasname='192.168.1.1', shortname='my-shortname', secret='my-secret')

fields_to_update = NasUpdate(secret="new-secret")
services.nas.update("192.168.1.1", nas_update=fields_to_update)

services.nas.get("192.168.1.1")
# Nas(nasname='192.168.1.1', shortname='my-shortname', secret='new-secret')

db_session.commit()
db_session.close()
```
