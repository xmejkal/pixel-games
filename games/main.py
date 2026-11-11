import app

knob = app.open_knob()
app.run(knob=knob, speaker=app.open_speaker(knob))
