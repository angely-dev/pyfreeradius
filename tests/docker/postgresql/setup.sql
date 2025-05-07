CREATE USER raduser WITH PASSWORD 'radpass';
GRANT CONNECT ON DATABASE raddb TO raduser;
GRANT pg_read_all_data TO raduser;
GRANT pg_write_all_data TO raduser;
