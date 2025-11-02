#!/bin/bash

# Chrome Version Downloader for nodriver
# Downloads Chrome versions 127 to latest using Chrome for Testing
# Uses official Google Chrome for Testing repository for stable, long-term downloads

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Base directory for chrome versions
CHROME_BASE_DIR="/home/tech/agent/chrome-version"

# Chrome for Testing base URL
CHROME_FOR_TESTING_URL="https://storage.googleapis.com/chrome-for-testing-public"

# JSON API URL for version information
VERSION_API_URL="https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"

# JSON API URL for channel versions (Beta, Dev, Canary)
CHANNEL_API_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"

# Version arrays - will be populated from API or use defaults
declare -A CHROME_VERSIONS=(
    ["113"]="113.0.5672.63"
    ["114"]="114.0.5735.133"
    ["115"]="115.0.5790.170"
    ["116"]="116.0.5845.96"
    ["117"]="117.0.5938.149"
    ["118"]="118.0.5993.70"
    ["119"]="119.0.6045.105"
    ["120"]="120.0.6099.109"
    ["121"]="121.0.6167.85"
    ["122"]="122.0.6261.94"
    ["123"]="123.0.6312.122"
    ["124"]="124.0.6367.207"
    ["125"]="125.0.6422.141"
    ["126"]="126.0.6478.126"
    ["127"]="127.0.6533.119"
    ["128"]="128.0.6613.137"
    ["129"]="129.0.6668.100"
    ["130"]="130.0.6723.116"
    ["131"]="131.0.6778.264"
    ["132"]="132.0.6834.110"
    ["133"]="133.0.6943.60"
    ["134"]="134.0.6998.52"
    ["135"]="135.0.7049.45"
    ["136"]="136.0.7103.54"
    ["137"]="137.0.7151.52"
    ["138"]="138.0.7204.39"
    ["139"]="139.0.7258.71"
    ["140"]="140.0.7339.46"
    ["141"]="141.0.7390.43"
    ["142"]="142.0.7444.59"
    ["143"]="143.0.7499.4"
    ["144"]="144.0.7500.2"
)

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to fetch latest versions from Chrome for Testing API
fetch_latest_versions() {
    print_info "Fetching latest version information from Chrome for Testing API..."

    local json_file="/tmp/chrome-versions.json"

    if wget -q -O "$json_file" "$VERSION_API_URL"; then
        print_success "Version information fetched successfully"

        # Parse JSON and update version array
        if command -v jq &> /dev/null; then
            local milestones=$(jq -r '.milestones | keys[]' "$json_file" 2>/dev/null)
            for milestone in $milestones; do
                if [ "$milestone" -ge 127 ]; then
                    local version=$(jq -r ".milestones[\"$milestone\"].version" "$json_file" 2>/dev/null)
                    if [ -n "$version" ] && [ "$version" != "null" ]; then
                        CHROME_VERSIONS["$milestone"]="$version"
                    fi
                fi
            done
            print_info "Updated versions for milestones 127+"
        else
            print_warning "jq not installed, using default version list"
        fi

        rm -f "$json_file"
    else
        print_warning "Failed to fetch version information, using default version list"
    fi
}

# Function to download and extract Chrome
download_chrome() {
    local version=$1
    local label="${2:-}"

    # Extract major version number
    local major_version=$(echo "$version" | cut -d. -f1)

    # Create version directory with label if provided
    if [ -n "$label" ]; then
        local version_dir="${CHROME_BASE_DIR}/${major_version}-${label}"
    else
        local version_dir="${CHROME_BASE_DIR}/${major_version}"
    fi

    # Check if already installed
    if [ -d "$version_dir" ] && [ -f "$version_dir/chrome-linux64/chrome" ]; then
        print_warning "Chrome ${major_version} (v${version}) already exists at $version_dir"
        return 0
    fi

    mkdir -p "$version_dir"

    print_info "Downloading Chrome ${major_version} (v${version})..."

    # Construct Chrome for Testing download URL
    local chrome_url="${CHROME_FOR_TESTING_URL}/${version}/linux64/chrome-linux64.zip"
    local zip_file="/tmp/chrome-${version}.zip"

    # Download with retry logic
    local max_retries=3
    local retry_count=0
    local download_success=false

    while [ $retry_count -lt $max_retries ]; do
        if wget -q --show-progress "$chrome_url" -O "$zip_file" 2>&1; then
            download_success=true
            break
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                print_warning "Download failed, retrying ($retry_count/$max_retries)..."
                sleep 2
            fi
        fi
    done

    if [ "$download_success" = false ]; then
        print_error "Failed to download Chrome ${major_version} (v${version}) after $max_retries attempts"
        print_warning "URL: $chrome_url"
        rm -f "$zip_file"
        return 1
    fi

    print_info "Extracting Chrome ${major_version} (v${version})..."

    # Extract the zip file
    if command -v unzip &> /dev/null; then
        unzip -q "$zip_file" -d "$version_dir"
    elif command -v python3 &> /dev/null; then
        python3 -c "import zipfile; zipfile.ZipFile('$zip_file').extractall('$version_dir')"
    else
        print_error "Neither unzip nor python3 found. Cannot extract zip file."
        rm -f "$zip_file"
        return 1
    fi

    # Clean up zip file
    rm -f "$zip_file"

    # Verify installation
    if [ -f "$version_dir/chrome-linux64/chrome" ]; then
        echo "$version" > "$version_dir/VERSION"
        echo "$major_version" > "$version_dir/MAJOR_VERSION"

        # Make chrome executable
        chmod +x "$version_dir/chrome-linux64/chrome"

        print_success "Chrome ${major_version} (v${version}) installed successfully"
        print_info "Location: $version_dir/chrome-linux64/chrome"
        return 0
    else
        print_error "Chrome binary not found after extraction"
        return 1
    fi
}

# Function to download all versions in a range
download_range() {
    local start_version=$1
    local end_version=$2

    print_info "Downloading Chrome versions ${start_version} to ${end_version}..."
    echo ""

    local success_count=0
    local fail_count=0
    local total=0

    # Sort and download versions
    for major in $(seq $start_version $end_version); do
        if [ -n "${CHROME_VERSIONS[$major]}" ]; then
            total=$((total + 1))
            if download_chrome "${CHROME_VERSIONS[$major]}"; then
                success_count=$((success_count + 1))
            else
                fail_count=$((fail_count + 1))
            fi
            echo ""
        fi
    done

    print_info "Downloaded: ${success_count}/${total} (Failed: ${fail_count})"
}

# Function to download and install a Chrome channel (Beta/Dev/Canary)
install_channel() {
    local channel_name=$1
    local install_dir="${CHROME_BASE_DIR}/${channel_name}"

    print_info "Fetching latest ${channel_name} version..."

    # Fetch channel version from API
    local versions_json=$(curl -s "$CHANNEL_API_URL")

    if [ -z "$versions_json" ]; then
        print_error "Failed to fetch channel version information"
        return 1
    fi

    # Extract version for the channel
    local version=$(echo "$versions_json" | jq -r ".channels.${channel_name^}.version" 2>/dev/null)

    if [ -z "$version" ] || [ "$version" = "null" ]; then
        print_error "Could not find version for ${channel_name} channel"
        return 1
    fi

    print_info "Latest ${channel_name} version: $version"

    # Check if already installed
    if [ -d "$install_dir" ] && [ -f "$install_dir/VERSION" ]; then
        local installed_version=$(cat "$install_dir/VERSION")
        if [ "$installed_version" = "$version" ]; then
            print_warning "${channel_name} $version is already installed"
            return 0
        else
            print_info "Upgrading from $installed_version to $version"
            rm -rf "$install_dir"
        fi
    fi

    # Create directory
    mkdir -p "$install_dir"

    # Download URL
    local download_url="${CHROME_FOR_TESTING_URL}/${version}/linux64/chrome-linux64.zip"
    local zip_file="/tmp/chrome-${channel_name}.zip"

    print_info "Downloading ${channel_name} from: $download_url"

    # Download with progress
    if wget -q --show-progress "$download_url" -O "$zip_file" 2>&1; then
        print_success "Download completed"
    else
        print_error "Failed to download ${channel_name} $version"
        rm -f "$zip_file"
        return 1
    fi

    # Extract
    print_info "Extracting..."
    if command -v unzip &> /dev/null; then
        unzip -q "$zip_file" -d "$install_dir"
    elif command -v python3 &> /dev/null; then
        python3 -m zipfile -e "$zip_file" "$install_dir"
    else
        print_error "Neither unzip nor python3 found. Cannot extract."
        rm -f "$zip_file"
        return 1
    fi
    rm -f "$zip_file"

    # Save version info
    echo "$version" > "$install_dir/VERSION"

    # Extract major version
    local major_version=$(echo "$version" | cut -d'.' -f1)
    echo "$major_version" > "$install_dir/MAJOR_VERSION"

    # Save channel name
    echo "$channel_name" > "$install_dir/CHANNEL"

    # Verify installation
    if [ -f "$install_dir/chrome-linux64/chrome" ]; then
        chmod +x "$install_dir/chrome-linux64/chrome"
        print_success "${channel_name} $version installed successfully"
        print_info "Location: $install_dir/chrome-linux64/chrome"
        return 0
    else
        print_error "Chrome binary not found after extraction"
        return 1
    fi
}

# Function to install all channels
install_all_channels() {
    print_info "Installing all Chrome channels (Beta, Dev, Canary)..."
    echo ""

    local success_count=0
    local fail_count=0

    for channel in beta dev canary; do
        if install_channel "$channel"; then
            success_count=$((success_count + 1))
        else
            fail_count=$((fail_count + 1))
        fi
        echo ""
    done

    print_info "Channels installed: ${success_count}/3 (Failed: ${fail_count})"
}

# Function to list installed versions
list_versions() {
    print_info "Installed Chrome versions:"
    echo ""

    if [ ! -d "$CHROME_BASE_DIR" ]; then
        print_warning "No Chrome versions installed yet"
        return
    fi

    local count=0
    for dir in "$CHROME_BASE_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/VERSION" ]; then
            local version=$(cat "$dir/VERSION")
            local major_version=$(cat "$dir/MAJOR_VERSION" 2>/dev/null || echo "?")
            local dirname=$(basename "$dir")
            local chrome_path="$dir/chrome-linux64/chrome"

            if [ -f "$chrome_path" ]; then
                echo -e "  ${GREEN}✓${NC} Chrome ${major_version} - v${version}"
                echo -e "    ${CYAN}Path:${NC} $chrome_path"
                count=$((count + 1))
            fi
        fi
    done

    echo ""
    if [ $count -eq 0 ]; then
        print_warning "No Chrome versions found"
    else
        print_info "Total: ${count} version(s) installed"
    fi
}

# Function to show usage
show_usage() {
    echo "Chrome Version Downloader"
    echo "Supports Stable versions (127-144) and Channels (Beta/Dev/Canary)"
    echo "Uses Chrome for Testing official repository"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  all                Download all Stable versions (127-144)"
    echo "  complete           Download all Stable versions + all Channels"
    echo "  range START END    Download Stable versions in range (e.g., 127 142)"
    echo "  version VER        Download specific version (e.g., 127.0.6533.119)"
    echo "  beta               Download Chrome Beta channel"
    echo "  dev                Download Chrome Dev channel"
    echo "  canary             Download Chrome Canary channel"
    echo "  channels           Download all channels (Beta, Dev, Canary)"
    echo "  update             Fetch latest version information from API"
    echo "  list               List all installed versions"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all                      # Download all Stable 127-144"
    echo "  $0 complete                 # Download all Stable + all Channels"
    echo "  $0 range 127 142            # Download Stable 127-142"
    echo "  $0 version 127.0.6533.119   # Download specific version"
    echo "  $0 beta                     # Download Beta channel only"
    echo "  $0 channels                 # Download all channels"
    echo "  $0 update                   # Update version database"
    echo "  $0 list                     # List installed versions"
    echo ""
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v wget &> /dev/null; then
        missing_deps+=("wget")
    fi

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    # Check for unzip or python3
    if ! command -v unzip &> /dev/null && ! command -v python3 &> /dev/null; then
        missing_deps+=("unzip or python3")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_info "Install with: sudo apt-get install ${missing_deps[*]}"
        return 1
    fi

    return 0
}

# Main script logic
main() {
    # Check dependencies first
    if ! check_dependencies; then
        exit 1
    fi

    # Create base directory
    mkdir -p "$CHROME_BASE_DIR"

    case "${1:-help}" in
        all)
            fetch_latest_versions
            download_range 127 144
            echo ""
            list_versions
            ;;
        complete)
            print_info "Installing all Stable versions + all Channels..."
            echo ""
            fetch_latest_versions
            download_range 127 144
            echo ""
            install_all_channels
            echo ""
            list_versions
            ;;
        range)
            if [ -z "$2" ] || [ -z "$3" ]; then
                print_error "Please specify start and end version numbers"
                show_usage
                exit 1
            fi
            fetch_latest_versions
            download_range "$2" "$3"
            echo ""
            list_versions
            ;;
        version)
            if [ -z "$2" ]; then
                print_error "Please specify a version number"
                show_usage
                exit 1
            fi
            download_chrome "$2" "${3:-}"
            ;;
        beta)
            install_channel "beta"
            echo ""
            list_versions
            ;;
        dev)
            install_channel "dev"
            echo ""
            list_versions
            ;;
        canary)
            install_channel "canary"
            echo ""
            list_versions
            ;;
        channels)
            install_all_channels
            echo ""
            list_versions
            ;;
        update)
            fetch_latest_versions
            print_success "Version database updated"
            echo ""
            print_info "Available Stable versions:"
            for major in $(seq 127 144); do
                if [ -n "${CHROME_VERSIONS[$major]}" ]; then
                    echo "  Chrome $major: ${CHROME_VERSIONS[$major]}"
                fi
            done
            ;;
        list)
            list_versions
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
