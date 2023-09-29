from common.constants import *

class Logger:
    global logLevel
    logLevel = LOG_LEVEL_INFO

    @staticmethod
    def SetLogLevel(_logLevel):
        global logLevel
        logLevel = _logLevel
        

    @staticmethod
    def LogDebug(message):
        if logLevel >=  LOG_LEVEL_DEBUG:
            print(f"{COLOR_PURPLE}[DEBUG]{COLOR_END} {message}")
    
    @staticmethod
    def LogError(message):
        if logLevel >=  LOG_LEVEL_ERROR:
            print(f"{COLOR_RED}[ERROR]{COLOR_END} {message}")
    
    @staticmethod
    def LogWarning(message):
        if logLevel >=  LOG_LEVEL_WARNING:
            print(f"{COLOR_YELLOW}[WARNING]{COLOR_END} {message}")

    @staticmethod
    def LogInfo(message):
        if logLevel >=  LOG_LEVEL_INFO:
            print(f"{COLOR_BLUE}[INFO]{COLOR_END} {message}")