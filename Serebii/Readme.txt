To shiny hunt the Serebii in VC, follow the steps:
(1) Already have the GC ball and stand in front of Ilex Forest Shrine.
(2) Check the global variables in "Serebii.py" and "ReturnControl.py", especially the server and client IP.
(3) Run "Serebii.py"
(4) When the hunter is running, the physical buttons are disabled.
(5) If you want to terminate the process, close the Python process and run the "ReturnControl.py". Then the physical buttons are back again.
(6) Check the time measured between "appear" and "go".
(7) For debugging, uncomment line 184 of "Serebii.py"
