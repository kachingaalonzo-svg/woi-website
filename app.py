@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")
    try:
        db = SessionLocal()
        users = db.query(User).order_by(User.created_at.desc()).all()
        members = db.query(Member).order_by(Member.created_at.desc()).all()
        donations = db.query(Donation).order_by(Donation.created_at.desc()).all()
        books = db.query(BookOrder).order_by(BookOrder.created_at.desc()).all()
        db.close()
        return render_template("admin.html", users=users, members=members, donations=donations, books=books)
    except Exception as e:
        print(f"Admin error: {e}")
        # If tables missing, recreate
        try:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            users = db.query(User).all()
            db.close()
            return render_template("admin.html", users=users, members=[], donations=[], books=[])
        except Exception as e2:
            return f"Admin error: {e} | {e2}. Please check Render logs."
