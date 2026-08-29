!identifiers hierarchical
hosting.cli -> hosting.master "Executes commands via REST/HTTP"
hosting.master -> hosting.database "Reads and writes state"

hosting.master -> hosting.webAgent "Controls and sends desired state via REST/HTTP"
hosting.webAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.dnsAgent "Controls and sends desired state via REST/HTTP"
hosting.dnsAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.mailAgent "Controls and sends desired state via REST/HTTP"
hosting.mailAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.dbAgent "Controls and sends desired state via REST/HTTP"
hosting.dbAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"
