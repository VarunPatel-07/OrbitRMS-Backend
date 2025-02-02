from Database.Database import db_dependencies


def upsert_record(
    db: db_dependencies, model, identifier_field, identifier_value, data: dict
):
    record = (
        db.query(model)
        .filter(getattr(model, identifier_field) == identifier_value)
        .first()
    )
    if record:
        for key, value in data.items():
            setattr(record, key, value)
        db.commit()
    else:
        new_record = model(**data)
        db.add(new_record)
        db.commit()
        
    return (record or new_record, data)
