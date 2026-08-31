dynamic hosting "HostingPlanCreation" {

    admin -> hosting.cli "Starts hosting plan creation command"

    hosting.cli -> hosting.master "Requests Hosting Plan creation via REST"

    hosting.master -> hosting.database "Creates Hosting Plan with resource limits and object limits"

    hosting.master -> hosting.cli "Returns Hosting Plan ID"

    hosting.cli -> admin "Shows created hosting plan"

    autoLayout lr
}
