![Docker Build](https://img.shields.io/github/workflow/status/p0lygun/pvc/Docker%20Build?label=Docker%20Build&style=for-the-badge)
# Private Voice Chat
A friendly Discord Bot to Create Private Voice Chats

## Features to Implement
- [ ] Persistent Bans

- [ ] Main Channel to Control the Creation of Channels
  - [x] Preset Names (2042, live stream and such)
  - [x] Custom Name
    - [x] Profanity Filter ?
    - [x] Reserved Keywords ?
  - [ ] ~~Start with already Locked VC~~
  - [x] Choose Region (and save or future Use)

IN VC chat
- [x] Button to toggle locked State
- [ ] ~~Interactive ban/unban/kick (choose name from dropdown / autocomplete slash command (only participants of the VC shown))~~
- [x] Change name via input field
- [ ] take ownership button
- [x] Ping when you join the VC (once a day)

## Custom Name Format
must be a string of len <= 50, 
keyword available  
$self$ -> name of the main vc  
$user$ -> username (gala)  
$tag$ -> tag of the user (gala#4315, the number after #, 4315)  
$rmoji$ -> random emoji  
