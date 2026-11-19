import { Badge, Button } from '@mantine/core';
import { Link } from 'react-router';
import { humanize } from '../lib/format';
import { supervisorColor, useOrgAction, usePersonOrg } from '../lib/org';

// The profile's org panel (PT-M2): unit, supervising partner, direct reports, and promotion
// (one level; a class-year step ahead of September is "accelerated"). Own firm only.
export function PersonOrgPanel({ slug, personId }: { slug: string; personId: number }) {
  const org = usePersonOrg(slug, personId);
  const action = useOrgAction(slug);
  if (!org.data) return null;
  const o = org.data;
  return (
    <div className="tst-panel" data-testid="person-org">
      <h3 className="tst-ptitle">Org</h3>
      <div className="tst-row">
        <span>Unit</span>
        <span>{o.unit_name}</span>
      </div>
      {o.leads && (
        <div className="tst-row">
          <span>Leads</span>
          <span>{o.leads.name}</span>
        </div>
      )}
      <div className="tst-row">
        <span>Supervising partner</span>
        <span>
          {o.supervisor ? (
            <>
              <Link to={`/game/${slug}/people/${o.supervisor.id}`}>{o.supervisor.name}</Link>
              {o.supervisor_label && (
                <Badge ml={6} size="xs" variant="light" color={supervisorColor(o.supervisor_label)}>
                  {o.supervisor_label}
                </Badge>
              )}
            </>
          ) : (
            '—'
          )}
        </span>
      </div>
      <div className="tst-row">
        <span>Direct reports</span>
        <span className="tst-num">{o.reports.length}</span>
      </div>
      {o.plans_owned > 0 && (
        <div className="tst-row">
          <span>Hiring plans run</span>
          <span className="tst-num">{o.plans_owned}</span>
        </div>
      )}
      {o.accelerated_years > 0 && (
        <div className="tst-row">
          <span>Accelerated</span>
          <span>
            {o.accelerated_years} class year{o.accelerated_years === 1 ? '' : 's'} ahead
          </span>
        </div>
      )}
      {o.promote_to && (
        <div className="tst-row">
          <span>Promotion</span>
          <Button
            size="xs"
            variant="light"
            loading={action.isPending}
            onClick={() => action.mutate({ kind: 'promote', personId })}
          >
            Promote to {humanize(o.promote_to)}
            {o.promotion_accelerated ? ' (accelerated)' : ''}
          </Button>
        </div>
      )}
      {action.error && (
        <div className="tst-row" style={{ color: 'var(--mantine-color-red-5)' }}>
          {action.error.message}
        </div>
      )}
    </div>
  );
}
