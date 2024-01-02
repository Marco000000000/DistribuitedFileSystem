local mysql = require("resty.mysql")

local mysql_query = "SELECT file_name FROM files WHERE ready=true;"

-- Create MySQL connection
local db, err = mysql:new()
if not db then
    ngx.say("Failed to instantiate MySQL: ", err)
    return
end

db:set_timeout(1000) -- 1 second timeout

local ok, err, errno, sqlstate = db:connect{
    host = "10.5.0.6",
    port = 3306,
    database = "ds_filesystem",
    user = "root",
    password = "giovanni",
}

if not ok then
    ngx.say("Failed to connect to MySQL: ", err, ": ", errno, " ", sqlstate)
    return
end

-- Perform MySQL query
local res, err, errno, sqlstate = db:query(mysql_query)
if not res then
    ngx.say("Bad result: ", err, ": ", errno, ": ", sqlstate, ".")
    return
end

-- Process the result
ngx.say("Query result:")
for i, row in ipairs(res) do
    for name, value in pairs(row) do
        ngx.say(name, ": ", value, " | ")
    end
    ngx.say("<br>")
end

-- Close the MySQL connection
db:close()
