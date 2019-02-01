from DeepQ import DeepQ


"""
    create the trading state from the batchsize by extracting the last 500 frames from the DataStream plus the state from the environment replay...
    What needs to be done

      OK0) Add the real bid & ask unmodified to the state array. 
        set the mean = 0 and the std = 1 for the columns that should not be changed...

      OK1) Make sure that the trading stops at the end of day. How? Must be in the state. force an action "go flat" at the EOD
         get_count returns the length for this day..
         for range(training_days)
            day_len=get_length(day)
            for range (seq_len, day_len)
               if i == day_len-1 -> EOD -> force action go flat..., set EOD = true. das gar nicht ausprobieren...
            statt game_over auch trade_over ... -> um den Reward richtig zu berechnen...
      OK3) Loop through the days and the states

      OK2) STATE: 
        State: Position, initrate, game_over, action, 
        Array to store:  
	a) 32 Features
        b) Position
        c) initial rate fractional / real 
        add b) and c) to the net
        set the initial rates...
        envionment get_batch so umbauen, dass es daten liefert
      OK4) Send the right data to the nets. Add position and init rate to the net in this process... 
      OK5) Model in eigenes Modul
      OK6) RL in Eigenes Modul, für threading

      20160621:
      -> check INDEXES of get_sequence() - es muessen genau sequence_length elemente sein, und sie muessen an der stelle current:index sitzen.
      TESTEN, ob t und t+1 ueberall im sinn der DeepQ sind!!!

      7) Epsillon skalieren...
      
"""

if __name__ == "__main__":
    d = DeepQ()
    d.execute()
