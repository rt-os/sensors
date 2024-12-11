#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h>

class Logger {
private:
    enum LogLevel { ERROR, MAIN, DEBUG };
    LogLevel currentLevel = DEBUG;

    void printPrefix(const char* levelName) {
        Serial.print("[");
        Serial.print(levelName);
        Serial.print("] ");
    }

public:
    void setLogLevel(int level) {
        currentLevel = static_cast<LogLevel>(level);
    }

    void error(const char* message) {
        if (currentLevel >= ERROR) log("ERROR", message);
    }

    void mainOutput(const String& message) {
        if (currentLevel >= MAIN) log("MAIN", message.c_str());
    }

    template <typename... Args>
    void debug(const Args&... args) {
        if (currentLevel >= DEBUG) {
            printPrefix("DEBUG");
            printArgs(args...);
            Serial.println();
        }
    }

private:
    void log(const char* level, const char* message) {
        printPrefix(level);
        Serial.println(message);
    }

    template <typename T>
    void printArgs(const T& arg) {
        Serial.print(arg);
    }

    template <typename T, typename... Args>
    void printArgs(const T& first, const Args&... rest) {
        Serial.print(first);
        printArgs(rest...);
    }
};

#endif