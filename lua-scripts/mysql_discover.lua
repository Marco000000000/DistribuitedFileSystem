-- mysql_request.lua

local mysql = require("resty.mysql")
local cjson = require("cjson")

local mysql_query = "SELECT file_name FROM file WHERE ready=true;"

-- MySQL connection settings
local db, err = mysql:new()
if not db then
    ngx.status = 500
    ngx.say("Failed to initialize MySQL: ", err)
    return
end

db:set_timeout(1000) -- 1 sec

local ok, err, errno, sqlstate = db:connect{
    host = "localhost",
    port = 3307,
    database = "ds_filesystem",
    user = "root",
    password = "giovanni",
}

if not ok then
    ngx.status = 500
    ngx.say("Failed to connect to MySQL: ", err)
    return
end

local res, err, errno, sqlstate = db:query(mysql_query)
if not res then
    ngx.status = 500
    ngx.say("Failed to query MySQL: ", err)
    return
end

-- Process the MySQL response as needed
ngx.say("Discover Response: ", cjson.encode(res))

-- Don't forget to close the MySQL connection
db:close()
