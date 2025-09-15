import crud

def test_crud_basic(db_session):
    # create
    obj = crud.create_audio(db_session, "/tmp/file.wav", 123)
    assert obj.id and obj.original_path.endswith(".wav")

    # get
    same = crud.get_audio(db_session, obj.id)
    assert same.id == obj.id and same.duration == 123

    # list
    items = crud.list_audio(db_session)
    assert obj in items
