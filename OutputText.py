import json
from deep_translator import GoogleTranslator

def output(guild_id, message):
    # Load the JSON file safely
    with open("cogs/jsonfiles/modify_text.json", "r") as j:
        text_modifiers = json.load(j)

    # Get the guild's settings safely
    guild_settings = text_modifiers.get(str(guild_id), {})

    # Use .get() to prevent KeyErrors and default to False
    reversed_text = guild_settings.get("reversed_text", False)
    australia_text = guild_settings.get("australia_text", False)
    balls_text = guild_settings.get("balls_text", False)
    language = guild_settings.get("language", "en")

    # Apply transformations based on the settings
    if reversed_text:
        return message[::-1]
    elif australia_text:
        word=message
        word=word.casefold()

        letter_index=["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z",",",".","!","?","1","2","3","4","5","6","7","8","9","0"]
        flipped_index=[592, 113, 596, 112, 477, 607, 387, 613, 7433, 638, 670, 108, 623, 117, 111, 100, 98, 633, 115, 647, 110, 652, 653, 120, 654, 122, 39, 729, 161, 191, 406, 4357, 400, 12579, 987, 57, 12581, 56, 54, 48]

        word = word[::-1]
        new_word=""
        for letter in word:
            if letter!=" " and (letter in letter_index):
                which_letter=letter_index.index(letter)
                new_word+=chr(flipped_index[which_letter])
            elif letter==" ":
                new_word+=" "
        
        return new_word
    
    
    elif balls_text:
        b_list=['98', '66', '7682', '7683', '7684', '7685', '7686', '7687', '579', '384', '7532', '7552', '385', '595', '386', '387', '1041', '1074', '1042', '914', '946', '388', '389', '595', '3647', '8383', '9837', '665']
        a_list=['97', '224', '513', '225', '226', '7845', '7847', '7849', '257', '227', '228', '479', '229', '507', '42809', '259', '7863', '515', '261', '462', '551', '481', '7681', '7843', '7834', '7843', '7857', '7859']
        l_list=['108', '76', '314', '313', '317', '7737', '7736', '7735', '7734', '318', '321', '322', '573', '410', '42825', '7930', '1340', '1388', '205', '8467', '1111', '620', '305', '523', '522', '237', '8466', '616']
        s_list=['115', '83', '350', '351', '348', '349', '537', '7784', '7785', '7780', '7781', '7776', '7777', '7782', '7783', '352', '353', '642', '346', '347', '66324', '36', '7779', '42920', '42921', '351', '424', '423']
        letters=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ' ', '%']

        alltext=message
        new_text=""
        for check in alltext:
            if check in letters:
                new_text+=check
        alltext=new_text
        while True:
            if len(alltext)%5!=0:
                alltext+="%"
            else:
                break
        count=0
        final_message=""
        for i in range(len(alltext)):
            if count==0:
                position=letters.index(alltext[i])
                convert=b_list[position]
                final_message+=chr(int(convert))
                count+=1
            elif count==1:
                position=letters.index(alltext[i])
                convert=a_list[position]
                final_message+=chr(int(convert))
                count+=1
            elif count==2:
                position=letters.index(alltext[i])
                convert=l_list[position]
                final_message+=chr(int(convert))
                count+=1
            elif count==3:
                position=letters.index(alltext[i])
                convert=l_list[position]
                final_message+=chr(int(convert))
                count+=1
            elif count==4:
                position=letters.index(alltext[i])
                convert=s_list[position]
                final_message+=chr(int(convert))
                count=0
                final_message+=" "
        return final_message
    
    elif language != "en":
        return GoogleTranslator(source='auto', target=language).translate(message)


    
    else:
        return message  # No modifications
