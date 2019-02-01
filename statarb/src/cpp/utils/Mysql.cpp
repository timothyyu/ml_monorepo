#include "Mysql.hpp"
#include <propertyutil.h>
#include <cstdlib>
#include <cppconn/statement.h>

sql::mysql::MySQL_Driver *Database::driver=NULL;

sql::mysql::MySQL_Driver *Database::getDriver()
{
	if (Database::driver==NULL)
	{
		Database::driver=sql::mysql::get_mysql_driver_instance();
	}

	return Database::driver;
}

sql::Connection *Database::getConnection(const char *file)
{
	PropertyUtil::PropertyMapT properties;
	PropertyUtil::read(file,properties);

	std::string url;
	url.append("tcp://");
	url.append(properties["host"]);
	url.append(":");
	url.append(properties["port"]);

	sql::Connection *con=Database::getDriver()->connect(url,properties["username"],properties["password"]);
	sql::Statement *stmt=con->createStatement();
	stmt->execute("USE "+properties["database"]);

	delete stmt;
	return con;
}

sql::Connection *Database::getConnection(std::string &file)
{
	return getConnection(file.c_str());
}

sql::Connection *Database::getConnection()
{
	return getConnection(getenv("DB_CONFIG_FILE"));
}
