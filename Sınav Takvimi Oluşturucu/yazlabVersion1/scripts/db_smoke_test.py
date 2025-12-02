from src.db.session import init_db, get_session
from src.db.models import Department
from src.db.models import Room

def run():
    init_db() 

    with get_session() as s:
        dep = s.query(Department).filter_by(name="Bilgisayar Mühendisliği").first()
        if not dep:
            dep = Department(name="Bilgisayar Mühendisliği")
            s.add(dep)
            s.commit()

        r = Room(
            department_id=dep.id,
            code="BM-101",
            name="Bilgisayar-101",
            capacity=60,
            rows=10,
            cols=6,
            group_size=2
        )
        s.add(r)
        s.commit()

        rooms = s.query(Room).all()
        print("Bu bölümdeki derslikler:", [(x.code, x.capacity) for x in rooms])

if __name__ == "__main__":
    run()
