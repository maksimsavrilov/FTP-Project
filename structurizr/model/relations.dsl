!identifiers hierarchical
hosting.cli -> hosting.master.api "Executes commands via REST/HTTP"
hosting.master -> hosting.database "Reads and writes state"
hosting.master.scheduler -> hosting.master.resources "Reads available resources"
hosting.master.scheduler -> hosting.master.nodes "Reads node capabilities and availability"
hosting.master.agentClient -> hosting.webAgent "Sends Web desired state via REST"
hosting.master.agentClient -> hosting.dnsAgent "Sends DNS desired state via REST"
hosting.master.agentClient -> hosting.mailAgent "Sends Mail desired state via REST"
hosting.master.agentClient -> hosting.dbAgent "Sends DB desired state via REST"
hosting.master.reconciliation -> hosting.master.services "Updates service state"
hosting.master.services -> hosting.cli "Returns service information"

hosting.master -> hosting.webAgent "Controls and sends desired state via REST/HTTP"
hosting.webAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.dnsAgent "Controls and sends desired state via REST/HTTP"
hosting.dnsAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.mailAgent "Controls and sends desired state via REST/HTTP"
hosting.mailAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"

hosting.master -> hosting.dbAgent "Controls and sends desired state via REST/HTTP"
hosting.dbAgent -> hosting.master "Reports actual state and heartbeat via REST/HTTP"
