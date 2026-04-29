# ─────────────────────────────────────────────
# 1. VPC y subred
# ─────────────────────────────────────────────

resource "google_compute_network" "hit2_vpc" {
  name                    = "hit2-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "hit2_subnet" {
  name          = "hit2-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.hit2_vpc.id
}

# ─────────────────────────────────────────────
# 2. Firewall rules
# ─────────────────────────────────────────────

resource "google_compute_firewall" "allow_ssh" {
  name    = "hit2-allow-ssh"
  network = google_compute_network.hit2_vpc.name
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["hit2-vm"]
}

resource "google_compute_firewall" "allow_rabbitmq" {
  name    = "hit2-allow-rabbitmq"
  network = google_compute_network.hit2_vpc.name
  allow {
    protocol = "tcp"
    ports    = ["5672", "15672"]
  }
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["hit2-rabbitmq"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "hit2-allow-internal"
  network = google_compute_network.hit2_vpc.name
  allow {
    protocol = "tcp"
  }
  allow {
    protocol = "icmp"
  }
  source_ranges = ["10.0.0.0/24"]
}

# ─────────────────────────────────────────────
# 3. VM RabbitMQ (fija, no se destruye entre runs)
# ─────────────────────────────────────────────

resource "google_compute_instance" "rabbitmq_vm" {
  name         = "hit2-rabbitmq"
  machine_type = var.rabbitmq_machine_type
  zone         = var.zone
  tags         = ["hit2-vm", "hit2-rabbitmq"]

  boot_disk {
    initialize_params {
      image = var.os_image
      size  = 20
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.hit2_subnet.id
    access_config {} # IP pública efímera
  }

  metadata_startup_script = templatefile(
    "${path.module}/../scripts/rabbitmq_bootstrap.sh",
    {
      rabbitmq_user = var.rabbitmq_user
      rabbitmq_pass = var.rabbitmq_pass
    }
  )

  metadata = {
    enable-oslogin = "TRUE"
  }
}

# ─────────────────────────────────────────────
# 4. VMs Worker (efímeras, count = num_workers)
# ─────────────────────────────────────────────

resource "google_compute_instance" "worker_vms" {
  count        = var.num_workers
  name         = "hit2-worker-${count.index + 1}"
  machine_type = var.worker_machine_type
  zone         = var.zone
  tags         = ["hit2-vm"]

  boot_disk {
    initialize_params {
      image = var.os_image
      size  = 20
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.hit2_subnet.id
    access_config {}
  }

  metadata_startup_script = templatefile(
    "${path.module}/../scripts/worker_bootstrap.sh.tpl",
    {
      worker_image  = var.worker_image
      rabbitmq_host = google_compute_instance.rabbitmq_vm.network_interface[0].network_ip
      rabbitmq_port = "5672"
      rabbitmq_user = var.rabbitmq_user
      rabbitmq_pass = var.rabbitmq_pass
    }
  )

  metadata = {
    enable-oslogin = "TRUE"
  }

  depends_on = [google_compute_instance.rabbitmq_vm]
}
