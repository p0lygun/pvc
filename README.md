# Private Voice Chat
A friendly Discord Bot to Create Private Voice Chats

## Features to Implement
- [ ] Persistent Bans

# Channel Types
|    Name     | Description                                                                                                                    |
|:-----------:|--------------------------------------------------------------------------------------------------------------------------------|
|  $VC-NAME$  | All the channels made via this vc will have the same name as the "main" vc                                                     |
| $USERNAME$  | The new vc will have the same name as the user who made the new vc                                                             |
|  $CUSTOM$   | Allows one to use [Custom Name Formatting](#custom-name-format) to name the new VC                                             |
| $INCREMENT$ | Is a special type of VC where all the child VC are made to follow a sequence allows one to use a special custom format $index$ |



## Custom Name Format
must be a string of len <= 50, 
keyword available  
$self$ -> name of the main vc  
$user$ -> username (gala)  
$tag$ -> tag of the user (gala#4315, the number after #, 4315)  
$rmoji$ -> random emoji  
$index$ -> The index of vc made by a increment vc (Only Available in INCREMENT vc type)  


