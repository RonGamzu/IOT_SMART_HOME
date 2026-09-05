
import io
import os
# Imports the Google Cloud client library
# pip install --upgrade google-cloud-texttospeech google-cloud-speech
from google.cloud import speech, texttospeech
# pip install sounddevice, scipy, soundfile
import sounddevice as sd
from scipy.io.wavfile import write
import soundfile as sf

path = os.getcwd()


credential_path = "C:\\Users\\yuzba\\Documents\\GitHub\\nlp-2021-494bf1773dbc.json"

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

sys_delay = 1 # sec
userresponcefile = 'c_input.wav'
ttsfile='c_output.wav'

class STT():
    def __init__(self):        
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=44100,
            language_code="en-US") 
        # Instantiates a client
        self.client = speech.SpeechClient()        

    def opensoundfile(self, file_name):        
        # Loads the audio into memory
        with io.open(file_name, "rb") as audio_file:
            content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
        return audio

    def recognize(self,audio):
        response = ''
        # Detects speech in the audio file and return results to caller
        try:
            response = self.client.recognize(config=self.config, audio=audio)
        except:
            print('Something wrong with recognition')
        return response    

class TTS():
    def __init__(self):        
        self.client = texttospeech.TextToSpeechClient() # Instantiates a client

    def tts_request(self, textstring):

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=textstring)

        # Build the voice request, select the language code ("en-US") and the ssml
        # voice gender ("neutral")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        return response

    def save2file(self, respond, outputfilename='current_tts.wav'):
        # The response's audio_content is binary.
        with open(outputfilename, 'wb') as out:
            # Write the response to the output file.
            out.write(respond.audio_content)
            print('Audio content written to file: ' + outputfilename)

class Player():
    def __init__(self):
        self.fs = 44100  # Sample rate
        self.seconds = 3  # Duration of recording
        self.AMP = 1  # Amplify data - increase Volume of sound        

    def record(self, recordfilepath):
        print(recordfilepath)
        try:                       
            print('Start recording') # TBD change record button color
            myrecording = sd.rec(int(self.seconds * self.fs), samplerate=self.fs, dtype='int16', channels=1)
            sd.wait()  # Wait until recording is finished            
            print('Stop recording')
            write(recordfilepath, self.fs, myrecording)  # Save as WAV file
        except:
            print('Failed in Record operation!')        

    def play(self, playfilepath):
        try:
            # Extract data and sampling rate from file
            data, fs = sf.read(playfilepath, dtype='float32')            
            print('Starting playing')
            sd.play(data*self.AMP, fs)
            sd.wait()  # Wait until file is done playing
            print('Stop playing')
        except:
            print('Failed in playfile operation!')

if __name__ == '__main__':
    # ttsfile = "Goodbye.wav"
    # ts = TTS()
    # print('Starting busyness logic example')
    # ts.save2file(ts.tts_request('ok, Good bye my friend'),ttsfile)
    # print('End of busyness logic example')
    # pl.play('Hello friend.wav')

    
    # pl.record(userresponcefile)
    # time.sleep(sys_delay)
    # try:        
    #     userresponcestring = st.recognize(st.opensoundfile(userresponcefile)).results[0].alternatives[0].transcript
    # except:
    #     userresponcestring  =''
    # icA(userresponcestring)
    pass



