import os
import pronouncing
import json
from Local_Voice.Fish_ESP32 import fish_performance_test
import asyncio


TIMINGS_JSON = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_output_timings/timings.json"


def main():

    #===================================| Seperate words and timings from json |===================#
    begin_times = []
    end_times= []
    words = []
    phonemes = []
    
    
    try:
        with open(TIMINGS_JSON, "r") as f:
            json_file = json.load(f)
    except Exception as e:
        print(f"Faild to load {TIMINGS_JSON}: {e}")

    # Loop through each word
    for i in range(len(json_file["fragments"])):
        word = str(json_file["fragments"][i]["lines"]).replace("[","").replace("]","").replace("'","") #
        begin_time = float(json_file["fragments"][i]["begin"])
        end_time = float(json_file["fragments"][i]["end"])
        
        words.append(word)
        begin_times.append(begin_time)
        end_times.append(end_time)
    
    #===================================| split words into phones |===================#
    print(words)
    for i in range(len(words)):
        words[i]=pronouncing.phones_for_word(words[i])
        if len(words[i]) >= 1:
            phonemes.append(words[i][0])

        # print(f"Word: {phonemes[i]}, Begin time: {begin_times[i]}, End time: {end_times[i]}")
    print("phonemes:",phonemes)
    
    #===================================| split phonemes with timings|========================
    
    vowels = ['A','E','I','O','U']
    delay = 0
    script = []
    total_time = 0
    for i in range(len(phonemes)):
        mouth_open = False
        begin_time = begin_times[i]
        end_time = end_times[i]
        delta_time = (end_time-begin_time) * 1000 # times 1000 because esp32 takes time in ms, not sec.
        total_time+=delta_time

        # splits each word into phonemes
        phoneme = phonemes[i].split(" ")

        #print("phoneme",phoneme)
        time_per_chunk = delta_time/len(phoneme)

        for chunk in phoneme:

            for letter in chunk:
                if letter in vowels:
                    mouth_open = True
                    break
                else:
                    mouth_open = False
            print(f"Chunk: {chunk}, mouth open: {mouth_open}, time per chunk: {time_per_chunk}")

            # Sets up script for mouth movement
            part = "mouth"
            state = "open" if mouth_open else "close"
            duration = time_per_chunk
            delay+=time_per_chunk

            move = {"part": part, "state": state, "duration": duration, "delay": delay}
            script.append(move)
        
    
    # Add head movement so head is up while fish is talking
    part = "head"
    state = "turn"
    duration = total_time
    delay = 0
    script.insert(0, {"part": part, "state": state, "duration": duration, "delay": delay})

    for i in script:
        print(i)



    #=================================| Set up the script list for export to ESP32 |========================
    
    asyncio.run(fish_performance_test(script))




if __name__ == "__main__":
    main()
    #asyncio.run(fish_performance_test())