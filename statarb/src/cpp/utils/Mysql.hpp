#ifndef MYSQL_HPP_
#define MYSQL_HPP_

#include <mysql_connection.h>
#include <mysql_driver.h>
#include <cppconn/connection.h>
#include <cppconn/driver.h>
#include <cppconn/exception.h>
#include <cppconn/metadata.h>
#include <cppconn/parameter_metadata.h>
#include <cppconn/resultset.h>
#include <cppconn/prepared_statement.h>
#include <cppconn/sqlstring.h>
#include <cppconn/statement.h>
#include <cppconn/warning.h>

class Database
{
private:
	static sql::mysql::MySQL_Driver *driver;
	static sql::mysql::MySQL_Driver *getDriver();
	Database();
public:
	static sql::Connection *getConnection(std::string &configFile);
	static sql::Connection *getConnection(const char *configFile);
	static sql::Connection *getConnection();
};

#endif /* MYSQL_HPP_ */
