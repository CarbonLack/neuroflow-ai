Intermediate products, logs, and provenance
===========================================

Intermediate data allow a result to be inspected, resumed, and explained.
Each completed stage creates human-readable outputs and a structured record.

Run record fields
-----------------

The audit entry includes time, project, stage, input reference, selected
channels, data range, tool and version, parameters, start/end time, status,
output location, warnings, error, and recovery route. Long operations continue
to display elapsed time and the latest log line in the fixed run footer.

Project recovery
----------------

The saved manifest restores source links, selected channels, electrode
metadata, QC, sorter registrations, active result, unit decisions, behavior
mapping, statistics, decoding, figure settings, AI discussion, approved plans,
and current workflow position.

AI evidence
-----------

The local context builder summarizes these records and removes paths and large
arrays before an optional model request. More structured evidence improves the
assistant's ability to cite the exact completed step, while the deterministic
record remains the authority.

Output status
-------------

Exports should label each capability as:

* validated with real data;
* validated with simulation only;
* interface available, validation pending.

A button, importable dependency, or planned adapter is not reported as a
completed scientific validation.
