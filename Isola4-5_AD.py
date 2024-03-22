# Versione aggiornata al 22/03/2024
# -----------------------------------------------------
# Controlli di inizio turno seguono la stessa logica dei controlli in frequenza: se la macchina finisce il ciclo aspetta.
# Lo spostamento è nel codice, vale 0,13

import streamlit as st
import simpy
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly_express as px
import math

st.set_page_config(page_title="Isole 4 - 5 AD", layout='wide')
my_cmap = plt.get_cmap("Reds")
st.markdown("# Isole 4 - 5 | Linea albero distribuzione")
st.sidebar.header("Isole 4 - 5 AD")
st.divider()

# versione aggiornata al 17/01/2024
# ISOLA 5 con 2 operatori funziona anche per isola 4 e per isola 2----------------------------------------------------------------------------------------------------------------------------------


def CQ(macchina, env, operatore, tcq, nome):
    while True:
        macchina.log.append('{:0.1f} | {} | Pezzo pronto per {}'.format(env.now, macchina.name, nome ))          
        yield env.timeout(0.1) #ritardo la chiamata in moodo da far prima caricare la macchina, il ritardo deve essere >= al tempo di carico scarico
        with operatore.request(priority=2) as req: 
            yield req # blocco la risorsa
            yield env.timeout(tcq) 
            op =  list(macchina.link_op.keys())[list(macchina.link_op.values()).index(operatore)]
            macchina.log.append('{:0.1f} | {} | Inizio {} | {}'.format(env.now-tcq, macchina.name, nome, op ))
            macchina.log.append('{:0.1f} | {} | Fine {} | {}'.format(env.now, macchina.name, nome, op ))
            
            macchina.link[operatore][0] += tcq

            #op =  list(macchina.link_op.keys())[list(macchina.link_op.values()).index(operatore)]
            macchina.log_op.append('{:0.1f}_{} | cq_macchina {} | + {} minuti'.format(env.now,op, macchina.name, tcq ))
            macchina.sat.append(tcq)             
        break   

def CQ_T(macchina, env, operatore, tcq, offset, nome): #a differenza del controllo a frequenza, qui l'offset ritarda il controllo per non farlo cadere per forza ad inizio turno
    while True:
        macchina.log.append('{:0.1f} | {} | Pezzo pronto per {}'.format(env.now, macchina.name, nome ))          
        yield env.timeout(offset) # ritardo a partire da cambio turno
        macchina.link[operatore][0] += tcq
        with operatore.request(priority=2) as req: 
            yield req # blocco la risorsa
            yield env.timeout(tcq) 
            op =  list(macchina.link_op.keys())[list(macchina.link_op.values()).index(operatore)]
            macchina.log.append('{:0.1f} | {} | Inizio {} | {}'.format(env.now-tcq, macchina.name, nome, op ))
            #st.write('{:0.1f} | {} | Inizio {}'.format(env.now-tcq, macchina.name, nome ))
            #st.write(macchina.sat_op)
            macchina.log.append('{:0.1f} | {} | Fine {} | {}'.format(env.now, macchina.name, nome, op ))
            
            macchina.link[operatore][0] += tcq
            #st.write(macchina.sat_op)                       
        break   

def Correzione(macchina, env, operatore, tc_corr):
    while True:               
        yield env.timeout(0) #ritardo la chiamata in moodo da far prima caricare la macchina, il ritardo deve essere >= al tempo di carico scarico
        with operatore.request(priority=1) as req: 
            yield req # blocco la risorsa
            yield env.timeout(tc_corr) 
            #print('{} | correzione fatta'.format(env.now))
            op =  list(macchina.link_op.keys())[list(macchina.link_op.values()).index(operatore)]
            macchina.log.append('{:0.1f} | {} | inizio correzione | {}'.format(env.now-tc_corr, macchina.name, op))
            macchina.log.append('{:0.1f} | {} | fine correzione | {}'.format(env.now, macchina.name, op))
            
            macchina.link[operatore][0] += tc_corr
        
        break               

def Other(macchina, env, operatore, tc, attività):
    while True:               
        yield env.timeout(0) #ritardo la chiamata in moodo da far prima caricare la macchina, il ritardo deve essere >= al tempo di carico scarico
        with operatore.request(priority=2) as req: 
            yield req # blocco la risorsa
            yield env.timeout(tc) 
            op =  list(macchina.link_op.keys())[list(macchina.link_op.values()).index(operatore)]
            macchina.log.append('{:0.1f} | {} | inizio {} | {}'.format(env.now-tc, macchina.name, attività, op))
            macchina.log.append('{:0.1f} | {} | fine {} | {}'.format(env.now, macchina.name, attività, op))
            
            macchina.link[operatore][0] += tc
        break   


#-----------------------------------------------------------------------------------------------------------------------------------------------------------     INIZIO DICHIARAZIONE CLASSE MACHINE

class Machine(object):
    
    def __init__(self, env, name, part, tempo_ciclo, carico_scarico,
                 batch, 
                 op_conduttore,
                 op_cambio_ut,
                 off_cu, periodo_cu, t_cambio_ut, 
                 offset_cq1 = 0, periodo_cq1 = 0, tempo_ciclo_cq1 = 0, op_cq1=None, # controlli a frequenza
                 offset_cq2 = 0, periodo_cq2= 0, tempo_ciclo_cq2 = 0, op_cq2=None,
                 offset_cq3 = 0, periodo_cq3 = 0, tempo_ciclo_cq3 = 0, op_cq3=None,
                 offset_cq4 = 0, periodo_cq4 = 0, tempo_ciclo_cq4 = 0, op_cq4=None,
                 offset_cq5 = 0, periodo_cq5 = 0, tempo_ciclo_cq5 = 0, op_cq5=None,
                 offset_ct1 = 0, tempo_ct1 = 0, op_ct1=None, # controlli 1/turno
                 offset_ct2 = 0, tempo_ct2 = 0, op_ct2=None,
                 offset_ct3 = 0, tempo_ct3 = 0, op_ct3=None,
                 tc_corr = 0, periodo_corr=0, op_corr=None,
                 tc_SAP = 0, periodo_SAP = 0, op_sap=None,
                 tc_part_in = 0, periodo_part_in = 0, op_in = None,
                 tc_part_out = 0, periodo_part_out = 0, op_out = None,                                 
                ):
        
        self.env = env
        self.name = name
        self.part = part
        self.tc = tempo_ciclo
        self.cs = carico_scarico
        self.batch = batch
        self.off_cu = off_cu

        self.link_op={'operatore1':operatore1,
                      'operatore2':operatore2
                      }

        #operatori 
        self.op_conduttore = self.link_op[op_conduttore]
        self.op_cambio_ut = self.link_op[op_cambio_ut]

        self.op_cq1 = self.link_op[op_cq1]

        try:
            self.op_cq2 = self.link_op[op_cq2]
        except:
            self.op_cq2 = None
        #----------------------------------------------------
        try:
            self.op_cq3 = self.link_op[op_cq3]
        except:
            self.op_cq3 = None
        #----------------------------------------------------
        try:
            self.op_cq4 = self.link_op[op_cq4]
        except:
            self.op_cq4 = None
        #----------------------------------------------------    
        try:
            self.op_cq5 = self.link_op[op_cq5]
        except:
            self.op_cq5 = None
        #----------------------------------------------------
        try:
            self.op_ct1 =  self.link_op[op_ct1]
        except:
            self.op_ct1 = None
        #----------------------------------------------------      
        try:
            self.op_ct2 =  self.link_op[op_ct2]
        except:
            self.op_ct2 = None
        #----------------------------------------------------
        try:
            self.op_ct3 =  self.link_op[op_ct3]
        except:
            self.op_ct3 = None
        #----------------------------------------------------
        self.op_corr = self.link_op[op_corr]
        self.op_sap  = self.link_op[op_sap]
        self.op_in = self.link_op[op_in]
        self.op_out = self.link_op[op_out]

        #saturazioni-----------------------------------------

        self.sat_op_conduttore = [0]
        self.sat_op_cambio_ut = [0]

        self.sat_op_cq1 = [0]
        self.sat_op_cq2 = [0]
        self.sat_op_cq3 = [0]
        self.sat_op_cq4 = [0]
        self.sat_op_cq5 = [0]

        self.sat_op_ct1 = [0]
        self.sat_op_ct2 = [0]
        self.sat_op_ct3 = [0]

        self.sat_op_corr = [0]
        self.sat_op_sap =  [0]
        self.sat_op_in = [0]
        self.sat_op_out = [0]

        # legami operatore - saturazione
        
        self.link = {self.op_conduttore : [0],
                self.op_cambio_ut : [0],
                self.op_cq1 : [0],
                self.op_cq2 : [0],
                self.op_cq3 : [0],
                self.op_cq4 : [0],
                self.op_cq5 : [0],
                self.op_ct1 : [0],
                self.op_ct2 : [0],
                self.op_ct3 : [0],
                self.op_corr : [0],
                self.op_sap : [0],
                self.op_in : [0],
                self.op_out : [0]}

        #tempi ciclo

        self.tc_corr = tc_corr
        self.periodo_corr = periodo_corr
        
        self.t_cambio_ut = t_cambio_ut
        self.periodo_cu = periodo_cu
        self.count_utensile = 0 + off_cu

        self.offset_ct1 = offset_ct1 # questi 3 offset servono per ritardare a piacere il contrllo 1T 
        self.offset_ct2 = offset_ct2 # e non farlo per forza al cambio turno
        self.offset_ct3 = offset_ct3

            
        self.log = []
        self.attese = []
        self.attesa_tot = 0
        self.pezzo_finito = 0
                       
        self.qc_count1 = 0 + offset_cq1
        self.qc_count2 = 0 + offset_cq2
        self.qc_count3 = 0 + offset_cq3
        self.qc_count4 = 0 + offset_cq4
        self.qc_count5 = 0 + offset_cq5

        
        self.sap_count = 4 # sfalsato
        self.part_in_count = 8 #sfalsato
        self.part_out_count = 8 #sfalsato
        
        self.corr_count = -1
        
        self.periodo_cq1 = periodo_cq1
        self.periodo_cq2 = periodo_cq2
        self.periodo_cq3 = periodo_cq3
        self.periodo_cq4 = periodo_cq4
        self.periodo_cq5 = periodo_cq5 # se non ho il controllo non viene mai incrementato il contatore e non si attiva mai la funzione

        self.periodo_SAP = periodo_SAP
        self.periodo_part_in = periodo_part_in
        self.periodo_part_out = periodo_part_out
                
        self.tempo_ciclo_cq1 = tempo_ciclo_cq1
        self.tempo_ciclo_cq2 = tempo_ciclo_cq2 
        self.tempo_ciclo_cq3 = tempo_ciclo_cq3
        self.tempo_ciclo_cq4 = tempo_ciclo_cq4 
        self.tempo_ciclo_cq5 = tempo_ciclo_cq5  
        self.tempo_ct1 = tempo_ct1
        self.tempo_ct2 = tempo_ct2
        self.tempo_ct3 = tempo_ct3

        self.tempo_ciclo_SAP = tc_SAP
        self.tc_part_in = tc_part_in
        self.tc_part_out = tc_part_out

        self.turno = 0  # il contatore turni serve per i controlli 1 a turno         
        self.turno_now = None

        #self.sat_op=0
        self.parts_made = 0        
        self.process = env.process(self.working()) #avvio l'istanza appena dopo averla creata
        
        self.log_op = []
        self.sat  = []


    def working(self): 
        while True:           
            with self.op_conduttore.request(priority=0) as req:
                    yield req                  
                    yield self.env.timeout(self.cs+0.13)  # x2 perchè lo spostamento dura uguale ----------------------modifica: self.cs + self.spostamento (che non esiste ad oggi negli input)
                    self.log.append('{:0.1f} | {} | Inizio carico-scarico'.format(env.now-self.cs, self.name))  
                    self.link[self.op_conduttore][0] += self.cs + 0.13 #* 2 # aumento la saturazione dell'operatore che esegue questa fase (il x2 è per considerare lo spostamento) 0.11 isola2
                    #self.tempo += self.cs
                    #self.log_op.append('{:0.1f} | saturazione  )
                    op =  list(self.link_op.keys())[list(self.link_op.values()).index(self.op_conduttore)]
                    self.log_op.append('{:0.1f}_{} | fine carico-scarico macchina {} | + {} minuti'.format(env.now,op, self.name, self.cs ))
                    self.sat.append(self.cs)

                
            yield self.env.timeout(self.tc)  #lavoro un pezzo  

            self.parts_made += self.batch 


            if self.tempo_ciclo_cq1 is not None:
                self.qc_count1 += self.batch
            if self.tempo_ciclo_cq2 is not None:     
                self.qc_count2 += self.batch
            if self.tempo_ciclo_cq3 is not None:
                self.qc_count3 += self.batch
            if self.tempo_ciclo_cq4 is not None:
                self.qc_count4 += self.batch
            if self.tempo_ciclo_cq5 is not None:
                self.qc_count5 += self.batch


            self.sap_count += self.batch  
            self.part_in_count += self.batch
                       
            self.corr_count += self.batch
            self.count_utensile  += self.batch
            
            self.log.append('{:0.1f} | {} | Avvio macchina '.format(env.now-self.tc, self.name)) 
            #self.log.append('{} | {} | Fine ciclo '.format(env.now, self.name))
                 
            if self.qc_count1==self.periodo_cq1: #se è il pezzo da controllare                
                env.process(CQ(self, env, self.op_cq1, self.tempo_ciclo_cq1, 'controllo qualità_1'))
                self.qc_count1=0
            
            if self.qc_count2==self.periodo_cq2: #se è il pezzo da controllare                
                env.process(CQ(self, env, self.op_cq2, self.tempo_ciclo_cq2, 'controllo qualità_2'))
                self.qc_count2=0
            
            if self.qc_count3==self.periodo_cq3: #se è il pezzo da controllare                
                env.process(CQ(self, env, self.op_cq3, self.tempo_ciclo_cq3, 'controllo qualità_3'))
                self.qc_count3=0
            
            if self.qc_count4==self.periodo_cq4: #se è il pezzo da controllare                
                env.process(CQ(self, env, self.op_cq4, self.tempo_ciclo_cq4, 'controllo qualità_4'))
                self.qc_count4=0
            
            if self.qc_count5==self.periodo_cq5: #se è il pezzo da controllare                
                env.process(CQ(self, env, self.op_cq5, self.tempo_ciclo_cq5, 'controllo qualità_5'))
                self.qc_count5=0
                                           
            if self.corr_count==self.periodo_corr:               
                env.process(Correzione(self, env, self.op_corr, self.tc_corr))#------questo è a macchina funzionante
                #with self.op_corr.request(priority=1) as req: 
                    #yield req # blocco la risorsa
                    #yield env.timeout(self.tc_corr) 

                    #op =  list(self.link_op.keys())[list(self.link_op.values()).index(self.op_corr)]
                    #self.log.append('{:0.1f} | {} | inizio correzione | {}'.format(env.now-self.tc_corr, macchina.name, op))
                    #self.log.append('{:0.1f} | {} | fine correzione | {}'.format(env.now, self.name, op))
            
                    #self.link[self.op_corr][0] += self.tc_corr

                self.corr_count=0
                                
            if self.sap_count==self.periodo_SAP:                 
                env.process(Other(self, env, self.op_sap, self.tempo_ciclo_SAP, 'avanzamento SAP'))
                self.sap_count=0
                
            if self.part_in_count==self.periodo_part_in:             
                env.process(Other(self, env, self.op_in, self.tc_part_in, 'Prelievo grezzi'))
                self.part_in_count=0

            self.turno_now = math.floor(env.now / 450)+1   

            if self.turno_now > self.turno:
                env.process(CQ_T(self, env, self.op_ct1, self.tempo_ct1, self.offset_ct1, 'Controllo a turno_1')) # nella isola4-5  il controllo 1Tè come quello degli altri controlli a frequenza
                self.turno = self.turno_now 
                #self.link[self.op_ct1][0] += self.tempo_ct1 # aggiungo solo la  quota saturazione, non chiamo la funzione seno fa controllo che ferma le macchiine
                # devo mettere anche gli altri controlli, ma solo se esistono : condizione if qualcosa is not None -----------------------------------------
#***controllo turno                
            self.log.append('{:0.1f} | {} | Fine ciclo | parts:{} '.format(env.now, self.name, self.parts_made))
            
            if self.t_cambio_ut != 0:
                #if self.count_utensile == self.periodo_cu:
                if self.count_utensile == self.periodo_cu:    
                    with self.op_cambio_ut.request(priority=1) as req: 
                        yield req # blocco la risorsa
                        yield env.timeout(self.t_cambio_ut)
                        self.log.append('{:0.1f}  | {} | pezzo °{} | Inizio cambio utensile'.format(env.now-self.t_cambio_ut, self.name, self.count_utensile))
                        self.log.append('{:0.1f}  | {} | Fine cambio utensile'.format(env.now, self.name))   
                        self.link[self.op_cambio_ut][0] += self.t_cambio_ut
                    self.count_utensile = 0

#-----------------------------------------------------------------------------------------------------------------------------------------------------------     FINE DICHIARAZIONE CLASSE MACHINE


env = simpy.Environment()
operatore1 = simpy.PriorityResource(env, capacity=1)
operatore2 = simpy.PriorityResource(env, capacity=1)
            

col1, col2, col3 = st.columns([1,1,2])
n = st.sidebar.number_input('Digitare il numero di macchine',step=1)

while n is None:
    st.stop()



machines = []
# Caricamento dati
for i in range (n):
    path = st.sidebar.file_uploader(f'Caricare il file di input della macchina {i+1}')
    if path is not None:
        st.subheader(f'Macchina {i+1}', divider='red')
        df=pd.read_excel(path)
        df_ciclo = df[['Ciclo macchina','Unnamed: 1']].dropna()
        df_ciclo = df_ciclo.rename(columns={'Unnamed: 1':'Valore'})
        df_frequenza = df[['Attività in frequenza','Unnamed: 4','Unnamed: 5','Unnamed: 6']].dropna()
        df_frequenza=df_frequenza[1:]
        df_frequenza = df_frequenza.rename(columns={'Attività in frequenza':'Nome attività',
                                                    'Unnamed: 4':'Periodo',
                                                    'Unnamed: 5':'Tempo ciclo',
                                                    'Unnamed: 6':'Operatore'})
        df_utensili = df[['Tabella utensili','Unnamed: 9','Unnamed: 10','Unnamed: 11']].dropna()       
        df_utensili = df_utensili[1:]
        df_utensili = df_utensili.rename(columns={'Unnamed: 9': 'Vita utensile [pezzi]',
                                                  'Unnamed: 10':'Tempo sostituzione [min]',
                                                  'Unnamed: 11':'Tempo correzione + ricontrollo [min]' })
        
        df_cq = df_frequenza[[('Controllo' in text) and ('Turno' not in text) and ('turno' not in text) for text in df_frequenza['Nome attività']]] #------------------------top class
        df_cq.reset_index(drop=True)

        df_turno = df_frequenza[[('Controllo' in text) and (('Turno' in text) or ('turno' in text)) for text in df_frequenza['Nome attività']]]
        df_turno.reset_index(drop=True)



#info  cambio  utensili
               
        
        freq_eq = 40
        df_utensili['new']=(df_utensili['Tempo sostituzione [min]']+df_utensili['Tempo correzione + ricontrollo [min]'])*freq_eq/df_utensili['Vita utensile [pezzi]']
#*** frequenza eq       
        t_eq = df_utensili.new.sum()
        df_utensili = df_utensili.drop('new',axis=1)

        
        # recupero info cq

        for j in range(5):
            try:
                t=df_cq.iloc[j,2]
                f=df_cq.iloc[j,1]
                o=df_cq.iloc[j,3]
                globals()[f't{j+1}']=t
                globals()[f'f{j+1}']=f
                globals()[f'op_cq{j+1}']=o
            except:
                globals()[f't{j+1}']=None
                globals()[f'f{j+1}']=None
                globals()[f'op_cq{j+1}']=None

        # recupero info controlli 1 a turno        

        for j in range(3):
            try:
                turno_t=df_turno.iloc[j,2]  
                ot=df_turno.iloc[j,3]
                globals()[f'turno_t{j+1}']=turno_t 
                globals()[f'op_ct{j+1}']=ot
            except:
                globals()[f'turno_t{j+1}']=None
                globals()[f'op_ct{j+1}']=None

        # recupero info correzione

        try:
            pos = df_frequenza[['Correzione' in text for text in df_frequenza[ 'Nome attività'] ]].index[0]
            periodo_cor = df_frequenza.loc[pos, 'Periodo']
            durata_cor = df_frequenza.loc[pos, 'Tempo ciclo']
            op_corr = df_frequenza.loc[pos, 'Operatore']
        except:
            periodo_cor = None
            durata_cor = None
            op_corr = None

        # recupero info SAP

        try:
            pos = df_frequenza[['SAP' in text for text in df_frequenza[ 'Nome attività'] ]].index[0]
            periodo_SAP = df_frequenza.loc[pos, 'Periodo']
            durata_SAP = df_frequenza.loc[pos, 'Tempo ciclo']
            op_sap = df_frequenza.loc[pos, 'Operatore']
        except:
            periodo_SAP = None
            durata_SAP = None
            op_sap = None

        # recupero info part_in

        try:
            pos = df_frequenza[['Prelievo' in text for text in df_frequenza[ 'Nome attività'] ]].index[0]
            periodo_part_in = df_frequenza.loc[pos, 'Periodo']
            durata_part_in = df_frequenza.loc[pos, 'Tempo ciclo']
            op_in = df_frequenza.loc[pos, 'Operatore']
        except:
            periodo_part_in = None
            durata_part_in = None
            op_in = None
        
        # recupero info part_out

        try:
            pos = df_frequenza[['TT' in text for text in df_frequenza[ 'Nome attività'] ]].index[0]
            periodo_part_out = df_frequenza.loc[pos, 'Periodo']
            durata_part_out = df_frequenza.loc[pos, 'Tempo ciclo']
            op_out = df_frequenza.loc[pos, 'Operatore']


        except:
            periodo_part_out = None
            durata_part_out = None
            op_out = None


 # creazione istanza della classe Machine

        macchina = Machine(env,
                           df_ciclo.loc[1,'Valore'],
                           df_ciclo.loc[2,'Valore'],
                           df_ciclo.loc[3,'Valore'],
                           df_ciclo.loc[4,'Valore'],
                           df_ciclo.loc[5,'Valore'],
                           df_ciclo.loc[6,'Valore'],
                           df_ciclo.loc[7,'Valore'],
                           i*10, freq_eq, t_eq, 
                           i, f1, t1, op_cq1,
                           i,f2,t2, op_cq2,
                           i,f3,t3, op_cq3,
                           i,f4,t4, op_cq4,
                           i,f5,t5, op_cq5,
                           i, turno_t1, op_ct1,
                           i*5, turno_t2, op_ct2,
                           i*8, turno_t3, op_ct3,
                           durata_cor, periodo_cor, op_corr,
                           durata_SAP, periodo_SAP, op_sap,
                           durata_part_in, periodo_part_in, op_in,
                           durata_part_out, periodo_part_out, op_out)
       
        machines.append(macchina)
   
        col1, col2, col3 = st.columns([1,2,1])
                     
        with col1:
            st.write('Parametri macchina')
            st.dataframe(df_ciclo, width=1000, height=250)
        with col2:
            st.write('Attività in frequenza')
            st.dataframe(df_frequenza, width=1000, height=250)
        with col3:
            st.write('Tabella vita utensili')
            st.dataframe(df_utensili, width=1500, height=250)
            st.write('Il cambio utensile richiede {:0.2f} minuti ogni 40 pezzi'.format(t_eq))
               
prodotti_finiti = st.sidebar.number_input('Macchine con output proodotto finito')

st.subheader('Simulazione', divider='red')
turni = st.number_input('Digitare la durata della simulazione [turni]',step=1)
if not turni:
    st.stop()
st.divider()

if turni != 0:

#if st.button('Start'):
    stop=turni*440

    env.run(until=stop)

    #op = 0

   # for macchina  in machines:
       # op += macchina.sat_op

    for macchina in machines:
        #st.write('Macchina: {} | Codice: {} | Output per turno: {:0.0f} | Ta_isola5: {:0.2f} | Ta_isola4: {:0.2f} '.format(macchina.name, macchina.part, macchina.parts_made/turni, (turni*450)/macchina.parts_made/(3), (turni*450)/macchina.parts_made/(2)))
        st.write(':red[Macchina: {}]'.format(macchina.name))
        st.write('Codice: _{}_   | Output per turno: :red[{:0.0f}] | Ta:{:0.2f} '.format(macchina.part, macchina.parts_made/turni, 450/(macchina.parts_made/turni)/prodotti_finiti))#-------------

    saturazione_1 = 0
    saturazione_2 = 0

    #tempo_1=0

#*** saturazione operatore
    for machine in machines:
        
        try:
            saturazione_1 += machine.link[machine.link_op['operatore1']][0]/(4.5*turni)
            #add = machine.link[machine.link_op['operatore1']][0]
            #tempo_1 += add
    
        except:
            saturazione_1 += 0        
        try:
            saturazione_2 += machine.link[machine.link_op['operatore2']][0]/(4.5*turni)
        except:
            saturazione_2 += 0


    st.divider()

    st.subheader('Saturazione OP1: {:0.2f}%'.format(saturazione_1))
    #st.subheader('Tempo OP1: {:0.0f}'.format(tempo_1))
    
    if saturazione_2 != 0:
        st.subheader('Saturazione OP2: {:0.2f}%'.format(saturazione_2))

    st.divider()



# Attese


   # frame = pd.DataFrame([item.split("|", 3) for item in machines[0].log])
   # frame = frame.rename(columns={0:"Minuto",1:"Macchina",2:"Descrizione", 3:"Part"})   
    #frame.Minuto = frame.Minuto.astype(float)
 #   dal data frame unico estraggo: frame_prod (relativo solo a carico-scarico), frame_cq (relativo solo a controlli qualità), per calcolare la durata delle fasi
  #  frame_prod = frame[(frame['Descrizione'] == ' Inizio carico-scarico') | (frame['Descrizione'] == ' Avvio macchina ') | (frame['Descrizione'] == ' Fine ciclo ')]
   # frame_prod = frame_prod.sort_values(by=['Minuto'])    
#    
 #   frame_prod = frame_prod.replace({' Inizio carico-scarico':'Carico-Scarico', ' Avvio macchina ':'Machining', ' Fine ciclo ':'Attesa operatore'})
  #  frame_prod['Durata'] = frame_prod.Minuto.shift(-1) - frame_prod.Minuto
   # st.write(frame_prod)
#    attese = frame_prod[frame_prod['Descrizione']=='Attesa operatore']
 #   st.write('Totale attesa: {:0.1f} minuti'.format(attese.Durata.sum()))
  #  st.write('Attesa max: {:0.1f} minuti'.format(attese.Durata.max()))
   # st.write('Attesa max: {:0.1f} minuti'.format(attese.Durata.max()))
#    fig = px.histogram(attese, x='Durata',
 #                     title='Distribuzione tempi di attesa operatore',
  #                     color_discrete_sequence=['red'])
#    st.plotly_chart(fig)
 #   st.write(machines[0].log)


# Costruzione dataframe per Gantt-------------------------------------------------------------------------------------------------------------------------------------------


incluso = ['Controllo','controllo','CONTROLLO',
           'Trasporto','trasporto','TRASPORTO',
           #'Correzione','correzione','CORREZIONE',
           'Prelievo','prelievo','PRELIEVO',
           'Sap','SAP','sap']

escluso = ['Pronto','pronto','PRONTO',
           'Correzione','correzione','CORREZIONE',
           ]

filtro_fine = ['Fine','fine','FINE']

# ciclo su n macchine-----------------------------------------------------------------------------------------------------------------------------------------------------------------

log_macchine = []
log_operatori = []

prog = 1
for macchina in machines:
    frame = pd.DataFrame([item.split("|", 3) for item in macchina.log])
    frame = frame.rename(columns={0:"Minuto",1:"Macchina",2:"Descrizione", 3:"Part"})   
    frame.Minuto = frame.Minuto.astype(float)

    # macchine

    frame_prod = frame[(frame['Descrizione'] == ' Inizio carico-scarico ') | (frame['Descrizione'] == ' Avvio macchina ') | (frame['Descrizione'] == ' Fine ciclo ')]
    frame_prod['Durata'] = frame_prod.Minuto.shift(-1) - frame_prod.Minuto
    frame_prod = frame_prod.replace({' Inizio carico-scarico ':'Carico-Scarico', ' Avvio macchina ':'Machining', ' Fine ciclo ':'Attesa operatore'})
    frame_prod['C{}'.format(prog)] = np.where(frame_prod['Descrizione']=='Carico-Scarico',frame_prod.Durata,0)
    frame_prod['M{}'.format(prog)] = np.where(frame_prod['Descrizione']=='Machining',frame_prod.Durata,0)
    frame_prod['A{}'.format(prog)] = np.where(frame_prod['Descrizione']=='Attesa operatore',frame_prod.Durata,0)

    # operatori

    frame_op = frame[[(any(check in desc for check in incluso) and (all(check not in desc for check in escluso))) for desc in frame.Descrizione]]
    frame_op['Durata'] = frame_op.Minuto.shift(-1) - frame_op.Minuto
    frame_op = frame_op[[(all(check not in desc for check in filtro_fine)) for desc in frame_op.Descrizione]]
    frame_op['Descrizione'] = frame_op['Descrizione'].str[8:]
    frame_op['Macchina'] = macchina.name
    frame_op['operatore1'] = np.where(frame_op.Part == ' operatore1', frame_op.Durata, 0)
    frame_op['operatore2'] = np.where(frame_op.Part == ' operatore2', frame_op.Durata, 0)
    frame_op['Label'] = frame_op.Macchina + " | " + frame_op.Descrizione 

    log_macchine.append(frame_prod)
    log_operatori.append(frame_op)
    
    prog += 1 



tempo = st.slider('Impostare intervallo gantt', 0, stop,(0, 100))
intervallo = tempo[1] - tempo[0]

gantt_op = pd.concat([logs for logs in log_operatori] )
gantt_macchine = pd.concat([logs for logs in log_macchine])

# qui deve essere filtrato il dataframe in base alla scelta

gantt_macchine = gantt_macchine[(gantt_macchine.Minuto > tempo[0]) & (gantt_macchine.Minuto < tempo[1]) ]
gantt_macchine = gantt_macchine.reset_index(drop=True)
gantt_op = gantt_op[(gantt_op.Minuto > tempo[0]) & (gantt_op.Minuto < tempo[1]) ]
gantt_op = gantt_op.sort_values(by=['Part','Minuto'])


# costruzione Gantt macchine

unique = gantt_macchine.Macchina.unique()

plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(20,5))
y_pos = np.arange(0,len(gantt_macchine), step=1)

for i in range(len(unique)):
    
    colonna = f'M{i+1}'

    
    #ax.barh(i*2, gantt_macchine.Minuto, color='black')
    #ax.barh(y_pos, gantt_macchine[colonna], left=gantt_macchine.Minuto, color=my_cmap(60*i))  
    ax.barh(i*2, gantt_macchine[colonna], left=gantt_macchine.Minuto, color=my_cmap(60*i))  
    ax.text(tempo[0]-15, i*2+0.1, unique[i], fontsize=12, color=my_cmap(60*i))


ax.invert_yaxis()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['left'].set_visible(True)
ax.grid('on', linewidth=0.2)
ax.tick_params(right=False, left=False, axis='y', color='r', length=16,grid_color='none')
ax.tick_params(axis='x', color='black', length=4, direction='in', width=4,labelcolor='w', grid_color='grey',labelsize=10)
ax.tick_params(axis='y', color='black', length=4, direction='in', width=4,labelcolor='w')
plt.xticks(np.arange(tempo[0],tempo[1],step=(intervallo/10)))
plt.yticks(np.arange(0,len(unique)*2 ,step=100))
plt.xlim(tempo[0]-20,tempo[1]+20)

# costruzione Gantt operatori

fig2, ax2 = plt.subplots(figsize=(20,7))
y_pos2 = np.arange(0,len(gantt_op), step=1)
operatori = ['operatore1','operatore2']
colori = {'operatore1': 'w', 'operatore2': 'red'}
for operatore in operatori:
    ax2.barh(y_pos2, gantt_op.Minuto, color='black')
    ax2.barh(y_pos2, gantt_op[operatore], left=gantt_op.Minuto, color=colori[operatore])

gantt_op['x_pos'] = gantt_op['Minuto'] + gantt_op['Durata'] + 1
for i in range(len(gantt_op)):
    x_pos = gantt_op.x_pos.iloc[i]
    ax2.text(x_pos, i, gantt_op.Label.iloc[i], fontsize=10, fontname='Avenir')#backgroundcolor='black')


ax2.text(tempo[0]-15, 2, 'Operatore1', fontsize=12)
ax2.text(tempo[0]-15, len(gantt_op)/2 + 2, 'Operatore2', color='red', fontsize=12)

ax2.invert_yaxis()
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['bottom'].set_visible(False)
ax2.spines['left'].set_visible(True)
ax2.grid('on', linewidth=0.2)
ax2.tick_params(right=False, left=False, axis='y', color='r', length=16,grid_color='none')
ax2.tick_params(axis='x', color='black', length=4, direction='in', width=4,labelcolor='w', grid_color='grey',labelsize=10)
ax2.tick_params(axis='y', color='black', length=4, direction='in', width=4,labelcolor='w')
plt.xticks(np.arange(tempo[0],tempo[1],step=(intervallo/10)))
plt.yticks(np.arange(0,len(gantt_op),step=20))
plt.xlim(tempo[0]-20,tempo[1]+20)


st.subheader('Gantt macchine')
st.pyplot(fig)

st.subheader('Gantt operatori')
st.pyplot(fig2)