from villager_info import VillagerInfo

import json


if __name__ == '__main__':
    with open('config.json') as f:
        config = json.load(f)

    bot = VillagerInfo(config)
    bot.run_forever()
