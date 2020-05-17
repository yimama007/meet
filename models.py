from server import db
from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.dialects.mysql import VARCHAR, DATETIME, BOOLEAN, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

db.drop_all()


class DepartmentLookup(db.Model):
    __tablename__ = 'department_lookup'

    id = Column(Integer, primary_key=True, autoincrement=1)
    token = Column(String(200), nullable=False, unique=True)
    department = Column(String(50), nullable=False, unique=True)


class Manager(db.Model):
    __tablename__ = 'manager'

    id = Column(Integer, primary_key=True, autoincrement=1)
    email = Column(VARCHAR(255), nullable=False, unique=True)
    _pass = Column('pass', VARCHAR(128), nullable=False)
    first_name = Column(VARCHAR(45), nullable=False)
    last_name = Column(VARCHAR(45), nullable=False)
    title = Column(VARCHAR(50), nullable=False)
    description = Column(VARCHAR(500), nullable=True)
    manager_dept_FK = Column(ForeignKey('department_lookup.id'), nullable=False, index=True)

    department_lookup = relationship('DepartmentLookup')

    def check_password(self, password):
        if self._pass == password:
            return True
        return False


class Employee(db.Model):
    __tablename__ = 'employee'

    id = Column(Integer, primary_key=True, autoincrement=1)
    token = Column(String(200), nullable=False, unique=True)
    first_name = Column(VARCHAR(45), nullable=False)
    last_name = Column(VARCHAR(45), nullable=False)
    user_dept_FK = Column(ForeignKey('department_lookup.token'), nullable=False, index=True)

    department_lookup = relationship('DepartmentLookup')


class Plan(db.Model):
    __tablename__ = 'plan'

    id = Column(Integer, primary_key=True, autoincrement=1)
    plan_name = Column(String(200), nullable=False, unique=True)
    funding_amount = Column(DECIMAL(12, 2), nullable=False)
    plan_justification = Column(VARCHAR(300), nullable=False)
    description = Column(VARCHAR(300), nullable=False)
    start_date = Column(DATETIME, nullable=False)
    end_date = Column(DATETIME, nullable=False)
    source_fund = Column(String(50), nullable=False) #should be a fk
    dest_fund = Column(String(50), nullable=False) #should be a fk
    fund_individuals = Column(BOOLEAN, nullable=False)
    control_name = Column(VARCHAR(50))
    control_window = Column(DATETIME)
    amount_limit = Column(DECIMAL(12, 2))
    usage_limit = Column(Integer)

    # add column for whether plan is complete or not

class PlanUser(db.Model):
    __tablename__ = 'plan_user'

    user_FK = Column(ForeignKey('employee.id'), primary_key=True, nullable=False)
    plan_FK = Column(ForeignKey('plan.id'), primary_key=True, nullable=False)

    employee = relationship('Employee')
    plan = relationship('Plan')


db.create_all()
