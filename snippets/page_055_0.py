def transition(self, case_id, expected, action, actor, now):
    if type(now) is not int or type(expected) is not int:
        raise ValueError("integer_clock_and_revision_required")
    with sqlite3.connect(self.path, isolation_level=None) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        _, state, revision, expires, owner, verifier, epoch = row
        if expected != revision:
            raise ValueError("stale_revision")
        if now >= expires:
            raise ValueError("expired")
        if action == "verify" and state == "review" and actor != owner:
            state, verifier = "verified", actor
        elif (action == "restore" and state == "verified"
              and actor not in (owner, verifier)):
            state, epoch = "restored", epoch + 1
        else:
            raise ValueError("invalid_transition_or_actor")
        db.execute("UPDATE cases SET state=?, revision=?, verifier=?, epoch=? "
                   "WHERE id=?", (state, revision + 1, verifier, epoch, case_id))
        db.commit()
    return self.read(case_id)