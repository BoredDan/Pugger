import sys
import pugger.bot

def main(*args):
    bot.init(*args)
    bot.client.close()
    
if __name__ == '__main__':
    sys.exit(main(*sys.argv))