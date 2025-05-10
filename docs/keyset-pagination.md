# Keyset pagination

Fetching all results at once is generally not needed nor recommended. There are two common options for pagination:

* Offset pagination (aka `LIMIT` + `OFFSET`) — not implemented
* **Keyset pagination (aka `WHERE` + `LIMIT`) — implemented**

In the era of infinite scrolling, the latter is generally preferred over the former. Not only is it better at performance but also simpler to implement.

## SQL explanation

There are many articles about keyset pagination ([here is one](https://use-the-index-luke.com/no-offset) and [another one](https://www.cockroachlabs.com/docs/stable/pagination.html)). The idea is to fetch limited results starting from a certain key.

> In general, that key is also a `KEY` or an `INDEX` in the SQL sense, which is used to speed up the lookup. This is the case in the FreeRADIUS database schema: username, groupname and nasname are all keys.

The query template looks like:

```sql
SELECT * FROM my_table
WHERE my_key > my_value
ORDER BY my_key
LIMIT 20
```

Because in our case the lookup occurs in different tables, the query must be adapted to:

```sql
-- Keyset pagination for fetching usernames
SELECT username FROM (
        SELECT DISTINCT username FROM radcheck
  UNION SELECT DISTINCT username FROM radreply
  UNION SELECT DISTINCT username FROM radusergroup
) u WHERE username > %s ORDER BY username LIMIT 100
```

The issue https://github.com/angely-dev/freeradius-api/issues/1 provides more explanation about query performance and DBMSes support. **In particular, the above SQL query breaks compatibility with Oracle Database and MSSQL which don't support `LIMIT` syntax.** If really needed, feel free to fork the project and adapt the queries for these DBMSes (solution is given in the issue).

> For now, this choice of breaking compatibility is assumed, considering that MySQL and PostgreSQL are more common for FreeRADIUS. Also, I still want to avoid an overkill ORM like SQLAlchemy for a rather simple project.
