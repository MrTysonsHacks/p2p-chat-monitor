
## Acknowledgements

 - [Based On XSS's Log Monitor](https://github.com/unhv/p2p-logs/tree/main)

This script parses P2P log files and sends chat events and/or quest completions to a discord server.

## Features

Choose to monitor chat (y/n)

Choose to monitor quest completions (y/n)

Choose check intervals in minutes. 

***Anything less than 5 minutes may cause instability with larger log files.***


## Usage
Open terminal to the location you downloaded the script to

```
python p2pchatmonitor.py
```


## Things to note


Chat Events - If your response is "BAD RESPONSE", from what I understand this means AI created a response but was denied by the bot for one reason or another.

Quest Completions - Only outputs when a quest is completed, does not currently output why a quest was not completed or skipped. Quest failure is planned for a future update. But I'm doing this on my free time, so it may be a while.
