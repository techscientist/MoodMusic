'''
Created on Mar 26, 2013

@author: Behrooz Afghahi
@version: 0.1

@note: the installNamespace functionality is very simple and it does not implement
keys and other SQL extras. for better performance consider creating the database
and passing the create table string to the runQuery method.

@warning: This module does not sanitized the data before execution. SQL INJECTION
is possible if the given data is not sanitized.

@note: for usage examples see : ./tests/data/SqLite_general.py
'''

import sqlite3
import config
from os import path

class SqLite(object):
    '''
    Provides interface to the SqLite database
    '''
    
    __connection = None
    __namespace = None
    __id = None
    __readBuffer = None

    def __init__(self, database = config.DEFAULT_DB):
        '''
        Constructor
        '''
        db_path = path.dirname(path.realpath(__file__)) + "/" + database + ".db"
        
        self.__connection = sqlite3.connect(db_path)
        
        self.__connection.row_factory = sqlite3.Row
    
    def setNamespace(self, namespace, id_field = "id"):
        '''
        Sets the current namespace used by the class and optionaly
        the primary key field name.
        @note: the second parameter is usefull when running with
               custom database structures where the id field is not id
        '''
        self.__namespace = namespace
        self.__id = id_field
    
    def getNamespace(self):
        '''
        Returns the current namespace
        '''
        return self.__namespace
    
    def getIdField(self):
        '''
        Returns the primary key of the database
        '''
        return self.__id
    
    def installNamespace(self, name, params):
        '''
        Creates a new database, it can be used to extend the functionality
        of the analysing plugins.
        Params is a dict in the form of {'name':'type', 'name':'type', ...}
        Where type is one of : NULL, INTEGER, REAL, TEXT, BLOB
        for more info: http://www.sqlite.org/datatype3.html
        '''
        
        if "id" in params:
            del params["id"]
        
        sql = "CREATE TABLE IF NOT EXISTS `" + name + "` ("
        sql += "`id` INTEGER PRIMARY KEY, "
        for field_name, field_type in params.items():
            sql += "`" + field_name + "` " + field_type + ","
        sql = sql[0:-1] + ")"
        
        result = self.runQuery(sql)
        
        if result:
            self.setNamespace(name)
        
        return result
    
    def hasNamespace(self):
        '''
        Checks if the namespace exists in the backend
        '''
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='"
        sql += self.getNamespace() + "'"
        
        cursor = self.__connection.cursor()
        cursor.execute(sql)
        
        if cursor.fetchall():
            return True
        else:
            return False
        
    def removeNamespace(self):
        '''
        Removes the current namespace.
        @warning: this operation removes all the data and is not reversable
        '''
        sql = "DROP TABLE IF EXISTS `" + self.getNamespace() + "`"
        
        return self.runQuery(sql)
        
    def runQuery(self, sql):
        '''
        Runs the sql query and commits the changes to file
        '''
        cursor = self.__connection.cursor()
        
        cursor.execute(sql)
        
        return self.__connection.commit()
    
    def write(self, params):
        '''
        Write information specified in params to database. paramas in the
        form {'field_name':'value', 'field_name':'value', ...}
        '''
        
        if not params:
            return True
        
        sql = self.__insert(params.keys())
        
        cursor = self.__connection.cursor()
        cursor.execute(sql, params.values())
        
        return self.__connection.commit()
    
    def writeMany(self, params):
        '''
        Write multiple records, params is in the form
        [{'field_name':'field_value', ...}, ...]
        '''
        
        if not params:
            return True
        
        sql = self.__insert(params[0].keys())
        
        values = []
        for value in params:
            values.append(value.values())
            
        cursor = self.__connection.cursor()
        cursor.executemany(sql, values)
        
        return self.__connection.commit()
        
    def __insert(self, field_names):
        '''
        Creates an INSERT SQL statement
        '''
        sql = "INSERT INTO `" + self.getNamespace() + "` ("
        sql += ", ".join(field_names) + " ) VALUES ( "
        sql += ", ".join("?" for i in range(len(field_names))) + " ) "
        
        return sql
    
    def search(self, cond = ''):
        '''
        Do a search based on cond.
        cond is a SQL condition in WHERE clause
        @return Void
        '''
        
        sql = "SELECT * FROM `" + self.getNamespace() + "`"
        
        if cond:
            sql += " WHERE " + cond
        
        cursor = self.__connection.cursor()
        cursor.execute(sql)
        self.__readBuffer = cursor
        
    def read(self, size = None):
        '''
        Read the result of the last search method call
        if size is ommited, all results are returned
        @return a list of results if size > 1 or ommited, one row if size = 1
                 and false if no search is done before this call
        '''
        if self.__readBuffer is None:
            return False
        
        if size is None:
            result = self.__readBuffer.fetchall()
            self.__readBuffer = None
        elif size == 1:
            result = self.__readBuffer.fetchone()
        else:
            result = self.__readBuffer.fetchmany(size)
        
        return result
    
    def deleteOne(self, item_id):
        '''
        Delete an item based on its id
        '''
        sql = "DELETE FROM `" + self.getNamespace() + "` WHERE `"
        sql += str(self.getIdField()) + "` = " + str(item_id)
        
        return self.runQuery(sql)
    
    def deleteMany(self, ids):
        '''
        Delete a list of items represented by their ids.
        ids is a list of id's
        '''
        cursor = self.__connection.cursor()
        
        for item_id in ids:
            sql = "DELETE FROM `" + self.getNamespace() + "` WHERE `"
            sql += str(self.getIdField()) + "` = " + str(item_id)
        
            cursor.execute(sql)
        
        return self.__connection.commit()

class C(object):
    '''
    Condition Class
    object oriented interface for creating SQL conditions
    '''
    
    @staticmethod
    def And(*args):
        '''
        Returns an AND condition from arbitary inputs
        '''
        return "(" + " AND ".join(args) + ")"
    
    @staticmethod
    def Or(*args):
        '''
        Returns an OR condition from arbitary inputs
        '''
        return "(" + " OR ".join(args) + ")"
    
    @staticmethod
    def _(field, operator, value):
        '''
        Returns a basic SQL equation.
        example: `title` = 'Album'
        '''
        return "`" + field + "` " + operator + " '" + str(value) + "'"
    
    @staticmethod
    def _raw(field, operator, value):
        '''
        Returns a basic SQL equation with an unquoted value
        example: _raw('id', 'IN', '(1,2,3)') = '`id` IN (1,2,3)'
        '''
        return "`" + field + "` " + operator + " " + str(value) + ""