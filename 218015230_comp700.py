# -*- coding: utf-8 -*-
"""218015230_COMP700.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rBgABsvLEbKa2WNdK5Orn-IAbwlK5RFE
"""

# 218015230 - Kailin Reddy
# Low resource machine translation

from google.colab import drive
drive.mount('/content/drive')

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import re
import string
from string import digits
import seaborn as sns
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from keras.layers import Input, LSTM, Embedding, Dense
from keras.models import Model
import tensorflow as tf
from tensorflow.keras import layers
import matplotlib.pyplot as plt

d = pd.read_excel('/content/drive/MyDrive/COMP700/1-2.xlsx')
d.head()

d.drop('Source.Name', inplace = True, axis=1)
d.columns = ['English', 'isiZulu']
d.head()

d = d[~pd.isnull(d['English'])]
d.drop_duplicates(inplace=True)
d[['English']] = d[['English']].astype(str)
d[['isiZulu']] = d[['isiZulu']].astype(str)

spcl = set(string.punctuation) #Special chars
dgt = str.maketrans('', '', digits) #Digits

# Convert to lowercase
d['English']=d['English'].apply(lambda x: x.lower())
d['isiZulu']=d['isiZulu'].apply(lambda x: x.lower())

# Remove quotes
d['English']=d['English'].apply(lambda x: re.sub("'", '', x))
d['isiZulu']=d['isiZulu'].apply(lambda x: re.sub("'", '', x))

#Remove all special chars
d['English']=d['English'].apply(lambda x: ''.join(ch for ch in x if ch not in spcl))
d['isiZulu']=d['isiZulu'].apply(lambda x: ''.join(ch for ch in x if ch not in spcl))

# Remove all numbers
d['English']=d['English'].apply(lambda x: x.translate(dgt))
d['isiZulu']=d['isiZulu'].apply(lambda x: x.translate(dgt))

# Remove extra spaces
d['English']=d['English'].apply(lambda x: x.strip())
d['isiZulu']=d['isiZulu'].apply(lambda x: x.strip())
d['English']=d['English'].apply(lambda x: re.sub(" +", " ", x))
d['isiZulu']=d['isiZulu'].apply(lambda x: re.sub(" +", " ", x))

d['isiZulu'] = d['isiZulu'].apply(lambda x: 'START_ ' + x + ' _END')

d['English length'] = d['English'].apply(lambda x:len(x.split(" ")))
d['isiZulu length'] = d['isiZulu'].apply(lambda x:len(x.split(" ")))
d.shape

d.head()

allEngWords = set()
for e in d['English']:
  for word in e.split():
    if word not in allEngWords:
      allEngWords.add(word)

allZuluWords = set()
for z in d['isiZulu']:
  for word in z.split():
    if word not in allZuluWords:
      allZuluWords.add(word)

text_map = {'English': d['English'], 'isiZulu':d['isiZulu']}

def dataframe_text(text_map):
    text_df=pd.DataFrame(text_map,columns=text_map.keys())
    for key in text_map.keys():
        text_df[key+' length']=text_df[key].apply(lambda text:len(text.split()))
    text_df=text_df.sample(frac=1)
    return text_df

text_df=dataframe_text(text_map)
text_df.head()

encoder_seq_length=max(text_df['English length'])
decoder_seq_length=max(text_df['isiZulu length'])

num_encoder_tokens=len(allEngWords)
num_decoder_tokens=len(allZuluWords)+1

english_lookup_table={word:num for num,word in enumerate(allEngWords)}
zulu_lookup_table={word:num+1 for num,word in enumerate(allZuluWords)}

english_token_lookup_table={num:word for word,num in english_lookup_table.items()}
zulu_token_lookup_table={num:word for word,num in zulu_lookup_table.items()}

def generate_batch(X,y,batch_size=32):
    while True:
        for i in range(0,len(X),batch_size):
            encoder_input_vector=np.zeros((batch_size,encoder_seq_length),dtype=np.float32)
            decoder_input_vector=np.zeros((batch_size,decoder_seq_length),dtype=np.float32)
            decoder_target_vector=np.zeros((batch_size,decoder_seq_length,num_decoder_tokens),dtype=np.float32)
            for j,(encoder_text,decoder_text) in enumerate(zip(X[i:i+batch_size],y[i:i+batch_size])):
                for time_step,encoder_word in enumerate(encoder_text.split()):
                    encoder_input_vector[j,time_step]=english_lookup_table[encoder_word]
                for time_step,decoder_word in enumerate(decoder_text.split()):
                    if time_step<len(decoder_text.split())-1:
                        decoder_input_vector[j,time_step]=zulu_lookup_table[decoder_word]
                    if time_step>0:
                        decoder_target_vector[j,time_step-1,zulu_lookup_table[decoder_word]]=1
            yield ([encoder_input_vector,decoder_input_vector],decoder_target_vector)

X=list(text_df['English'])
y=list(text_df['isiZulu'])

X_train=X[:len(X)*80//100]
y_train=y[:len(y)*80//100]
X_valid=X[80*len(X)//100:]
y_valid=y[80*len(y)//100:]

latent_dim=512
embedding_dim=256
batch_size=128

encoder_inputs=layers.Input(shape=(None,))
encoder_embedding_layer=layers.Embedding(
    input_dim=num_encoder_tokens,output_dim=embedding_dim,
    mask_zero=True
)
encoder_embeddings=encoder_embedding_layer(encoder_inputs)
encoder_lstm=layers.Bidirectional(layers.LSTM(units=latent_dim,return_state=True))
_,encoder_hidden_state1,encoder_cell_state1,encoder_hidden_state2,encoder_cell_state2=encoder_lstm(encoder_embeddings)
encoder_state=[encoder_hidden_state1+encoder_hidden_state2,encoder_cell_state1+encoder_cell_state2]


decoder_inputs=layers.Input(shape=(None,))
decoder_embedding_layer=layers.Embedding(
    input_dim=num_decoder_tokens,output_dim=embedding_dim,
    mask_zero=True
)
decoder_embeddings=decoder_embedding_layer(decoder_inputs)
decoder_lstm=layers.LSTM(units=latent_dim,return_sequences=True,return_state=True)
decoder_output,_,_=decoder_lstm(decoder_embeddings,initial_state=encoder_state)
output_layer=layers.Dense(units=num_decoder_tokens)
decoder_output=output_layer(decoder_output)
output_probs=tf.nn.softmax(decoder_output)


model=tf.keras.models.Model(inputs=(encoder_inputs,decoder_inputs),outputs=output_probs)
model.summary()

model.compile(optimizer='adam',loss='categorical_crossentropy')

history=model.fit(
    x=generate_batch(X_train,y_train),
    validation_data=generate_batch(X_valid,y_valid),
    batch_size=batch_size,
    epochs=5,
    steps_per_epoch=len(X_train)//batch_size,
    validation_steps=len(X_valid)//batch_size
)

encoder_model=tf.keras.models.Model(inputs=encoder_inputs,outputs=encoder_state)

decoder_hidden_state=layers.Input(shape=(latent_dim,))
decoder_cell_state=layers.Input(shape=(latent_dim,))
decoder_init_state=[decoder_hidden_state,decoder_cell_state]
decoder_embeddings=decoder_embedding_layer(decoder_inputs)
decoder_output,decoder_output_hidden_state,decoder_output_cell_state=decoder_lstm(decoder_embeddings
                                                                    ,initial_state=decoder_init_state)
decoder_final_state=[decoder_output_hidden_state,decoder_output_cell_state]
decoder_output=output_layer(decoder_output)
decoder_probs=tf.nn.softmax(decoder_output)
decoder_model=tf.keras.models.Model(inputs=[decoder_inputs]+decoder_init_state
                                    ,outputs=[decoder_probs]+decoder_final_state)

encoder_model.summary()

decoder_model.summary()

def generate_text(text):
    translation=""
    states_value=encoder_model(text)
    target=np.zeros((1,1))
    target[0,0]=zulu_lookup_table['START_']
    stop_condition=False
    while not stop_condition:
        output_token,hidden_state,cell_state=decoder_model([target]+states_value)
        char_index=np.argmax(output_token[0,-1,:])
        char=zulu_token_lookup_table[char_index]
        if char=='_END' or len(translation)>=decoder_seq_length:
            stop_condition=True
            continue
        translation+=' '+char
        states_value=[hidden_state,cell_state]
        target[0,0]=zulu_lookup_table[char]
    return translation

text_gen=generate_batch(X_valid,y_valid,batch_size=1)
text_gen
k=-1

pd.DataFrame(history.history).plot()
plt.title("Loss")
plt.show()

k+=1
[encoder_inputs,decoder_inputs],decoder_target=next(text_gen)
print(f'Input sentence: {X_valid[k:k+1][0]}')
print(f'Actual translation: {y_valid[k:k+1][0][5:-5]}')
print(f"Model's translation: {generate_text(encoder_inputs)}" )

from nltk.translate.bleu_score import sentence_bleu
test_eng_texts = [pair[0] for pair in y_valid]
test_zul_texts = [pair[1] for pair in y_valid]
score = 0
bleu  = 0
for i in range(10):
    
    candidate = y_valid[i]
    
    reference = test_zul_texts[i].lower()
    print(candidate,reference)
    score = sentence_bleu(reference, candidate, weights=(1, 0, 0, 0))
    bleu+=score
    print(f"Score:{score}")
print(f"\nBLEU score : {round(bleu,2)}/10")