"""python -m analytics.export --output exports (admin/operator command)."""
import argparse
import json
import pandas as pd
from pathlib import Path
from sqlalchemy import select
from apps.api.db import Event, ResearchExport, SessionLocal, User
from apps.api.main import refresh, serialize
from apps.api.privacy import consenting_events
from .etl import reconstruct, user_frame
from .stats import analyze

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='exports')
    parser.add_argument('--experience',choices=('guided','chat'),default='guided')
    args=parser.parse_args()
    path=Path(args.output);path.mkdir(parents=True,exist_ok=True)
    with SessionLocal() as db:
        events=[serialize(e) for e in db.scalars(consenting_events())]
        rows=[r for r in reconstruct(events) if r.get('experience','guided')==args.experience]
        frame=user_frame(rows)
        output=analyze(frame)
        output['experience']=args.experience
        frame.to_csv(path/'participants.csv',index=False)
        pd.DataFrame(rows).to_csv(path/'sessions.csv',index=False)
        from .etl import effective
        reflections = [dict(user_id=e['user_id'], session_id=e['session_id'], event_type=e['event_type'],
                            created_at=e['created_at'], text=e['payload'].get('justification', e['payload'].get('reasoning')))
                       for e in effective(events) if e['event_type'] in ('verification_submitted', 'evaluation_submitted') and e['session_id'] in {r['session_id'] for r in rows}]
        pd.DataFrame(reflections, columns=['user_id', 'session_id', 'event_type', 'created_at', 'text']).to_csv(path/'reflections.csv',index=False)
        (path/'analysis.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
        lines=['# ThinkFirst comparison', '', 'Reference values are quoted from the specification; the original paper was not supplied.', '',
               '| Analysis | Paper reference | Behavioral data |','| --- | --- | --- |',
               f"| Logistic OR | 2.114 (p < 0.001) | {output['logistic']} |"]
        for row in output['mann_whitney']:
            lines.append(f"| {row['metric']} | Not supplied | {row} |")
        lines.extend(['','Different measurement scales prevent direct coefficient equivalence. See docs/decisions.md.'])
        (path/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
        db.add(ResearchExport(data=output))
        for user in db.scalars(select(User).with_for_update()): refresh(db,user.id)
        db.commit()
    print(f'Exported {len(frame)} participants to {path.resolve()}')

if __name__=='__main__': main()
